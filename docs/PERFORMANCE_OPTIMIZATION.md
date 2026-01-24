# Performance Optimization Analysis and Implementation

> **Task #29**: Systematic performance optimization of DI Agent and foundation system
>
> **Date**: 2026-01-24
> **Status**: Analysis Complete, Implementation In Progress

## Executive Summary

This document analyzes performance bottlenecks in the DI Agent and foundation extraction system and implements optimizations to meet target latencies:

**Targets:**
- DI Agent invocation: < 5 seconds (p95)
- Foundation extraction: < 10 seconds per extraction (p95)
- Readiness computation: < 2 seconds (p95)
- Cache hit rate: > 80%

**Current State Analysis:**
- ⚠️ **Sequential DB calls**: Up to 15 sequential database queries per DI Agent invocation
- ⚠️ **Redundant cache checks**: `is_cache_valid` calls `get_di_cache` twice
- ⚠️ **No readiness caching**: Readiness computed fresh every time
- ⚠️ **Inefficient signal filtering**: Fetches all signals then filters in Python
- ✅ **Good**: DI cache exists with reasonable TTL (60 min)

---

## 1. Performance Profiling

### 1.1 DI Agent Invocation Flow

**File**: `app/agents/di_agent.py` (lines 60-86)

```python
# Current sequential flow:
state_snapshot = get_state_snapshot(project_id)        # DB call 1
readiness = compute_readiness(project_id)              # DB calls 2-10 (via _fetch_project_state)
di_cache = get_di_cache(project_id)                    # DB call 11
cache_valid = is_cache_valid(project_id)               # Calls get_di_cache AGAIN + unanalyzed signals
unanalyzed = get_unanalyzed_signals(project_id)        # Calls get_di_cache AGAIN + all signals
```

**Issues:**
1. **Sequential execution**: ~15 DB calls executed serially
2. **Redundant cache fetches**: `get_di_cache` called 3+ times
3. **Redundant data fetches**: `get_unanalyzed_signals` refetches cache and all signals

**Estimated Time**:
- 15 DB calls × ~200ms each (average Supabase query) = **~3 seconds just in DB I/O**
- Plus LLM call (1-3 seconds) = **Total: 4-6 seconds**

### 1.2 Readiness Computation Flow

**File**: `app/core/readiness/score.py` (lines 214-229)

```python
def _fetch_project_state(project_id: UUID) -> dict:
    vp_steps = list_vp_steps(project_id)                # DB call 1
    features = list_features(project_id)                # DB call 2
    personas = list_personas(project_id)                # DB call 3
    strategic_context = get_strategic_context(project_id)  # DB call 4
    signals_result = list_project_signals(project_id)   # DB call 5
    meetings = list_meetings(project_id)                # DB call 6
    foundation = get_project_foundation(project_id)     # DB call 7
```

**Issues:**
1. **Sequential execution**: 7 DB calls executed serially
2. **No caching**: Comment says "Always computed fresh from current state (no caching)"
3. **Full entity loads**: Fetches all entities even when only counts are needed

**Estimated Time**:
- 7 DB calls × ~200ms each = **~1.4 seconds**
- Plus dimension scoring (minimal) = **Total: ~1.5 seconds**

### 1.3 Cache Inefficiencies

**File**: `app/db/di_cache.py`

**Issue 1: Redundant Cache Fetches**

```python
def is_cache_valid(project_id: UUID) -> bool:
    cache = get_di_cache(project_id)  # DB call
    # ...
    unanalyzed = get_unanalyzed_signals(project_id)  # Calls get_di_cache AGAIN

def get_unanalyzed_signals(project_id: UUID) -> list[dict]:
    cache = get_di_cache(project_id)  # DB call (duplicate!)
    analyzed_ids = cache.signals_analyzed if cache else []
    # Fetch ALL signals
    all_signals_response = supabase.table("signals").select("*").eq(...)
```

**Issue 2: Inefficient Signal Filtering**

```python
# Fetches ALL signals, then filters in Python
all_signals = all_signals_response.data or []
unanalyzed = [s for s in all_signals if str(s["id"]) not in analyzed_ids]
```

Could use database filtering: `WHERE id NOT IN (analyzed_ids)` or `WHERE created_at > last_analysis_at`

**Issue 3: Long Cache TTL**

```python
CACHE_VALIDITY_MINUTES = 60  # 1 hour
```

This is reasonable for DI cache (agent analysis state), but may be too aggressive for some use cases.

---

## 2. Optimization Strategy

### Priority 1: Parallel Data Loading (HIGH IMPACT)

**Target**: Reduce DB I/O from ~3 seconds to < 500ms

**Implementation**:
1. Make all data access functions async
2. Use `asyncio.gather()` to parallelize independent DB calls
3. Pass cached data between functions to avoid refetching

**Approach**:
- Create async versions of DB functions (or make existing ones async)
- Use connection pooling to handle concurrent queries
- Implement request-scoped caching (pass fetched data as params)

### Priority 2: Readiness Caching (MEDIUM IMPACT)

**Target**: Reduce readiness computation from ~1.5s to < 100ms (cache hit)

**Implementation**:
1. Cache readiness result in `readiness_cache` table (already exists!)
2. Cache TTL: 5 minutes (vs current "never cached")
3. Invalidate on foundation/entity changes
4. Include `computed_at` timestamp for staleness checks

**Tradeoffs**:
- Cache hit = instant (< 100ms)
- Cache miss = same as current (~1.5s)
- Slight risk of stale data (mitigated by short TTL + invalidation hooks)

### Priority 3: Database Query Optimization (MEDIUM IMPACT)

**Target**: Reduce per-query overhead by 20-30%

**Implementation**:
1. Add database indexes on foreign keys
2. Use `SELECT COUNT(*)` instead of fetching full entities when only counts needed
3. Filter signals at database level, not in Python
4. Batch signal queries with WHERE IN clauses

### Priority 4: Cache Strategy Refinement (LOW IMPACT)

**Target**: Improve cache hit rate from unknown to > 80%

**Implementation**:
1. Add cache hit/miss logging
2. Tune TTLs based on usage patterns
3. Implement granular invalidation (partial cache updates)
4. Add cache warming for common queries

---

## 3. Implementation Plan

### Phase 1: Quick Wins (2-4 hours)

#### 3.1 Fix Redundant Cache Fetches

**File**: `app/agents/di_agent.py`

**Before**:
```python
di_cache = get_di_cache(project_id)
cache_valid = is_cache_valid(project_id)  # Refetches cache
unanalyzed = get_unanalyzed_signals(project_id)  # Refetches cache AND signals
```

**After**:
```python
di_cache = get_di_cache(project_id)
unanalyzed = get_unanalyzed_signals_optimized(project_id, di_cache)  # Pass cache
cache_valid = _is_cache_valid_from_data(di_cache, unanalyzed)  # Use data, no DB calls
```

**Impact**: Eliminates 2-3 redundant DB calls (saves ~400-600ms)

---

#### 3.2 Optimize Signal Filtering

**File**: `app/db/di_cache.py`

**Before**:
```python
# Fetch ALL signals, filter in Python
all_signals = supabase.table("signals").select("*").eq("project_id", str(project_id)).execute()
unanalyzed = [s for s in all_signals.data if str(s["id"]) not in analyzed_ids]
```

**After (Option 1 - Use database filtering)**:
```python
# Let database do the filtering
if analyzed_ids:
    # Postgres: WHERE id NOT IN (...)
    unanalyzed = (
        supabase.table("signals")
        .select("*")
        .eq("project_id", str(project_id))
        .not_.in_("id", analyzed_ids)  # Database-side filtering
        .execute()
    ).data
else:
    # No analyzed signals yet, all are unanalyzed
    unanalyzed = (
        supabase.table("signals")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    ).data
```

**After (Option 2 - Use timestamp-based filtering)**:
```python
# Even better: use timestamp instead of ID list
last_analysis_at = cache.last_signal_analyzed_at if cache else None
if last_analysis_at:
    unanalyzed = (
        supabase.table("signals")
        .select("*")
        .eq("project_id", str(project_id))
        .gt("created_at", last_analysis_at)  # Only new signals
        .execute()
    ).data
else:
    # No analysis yet, fetch all
    unanalyzed = (
        supabase.table("signals")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    ).data
```

**Impact**: Reduces data transfer and filtering overhead (saves ~100-300ms for projects with many signals)

---

#### 3.3 Add Timing Instrumentation

**File**: `app/core/logging.py` (create performance utilities)

```python
import time
from contextlib import contextmanager
from app.core.logging import get_logger

logger = get_logger(__name__)

@contextmanager
def timer(operation_name: str, project_id: str = None):
    """Context manager for timing operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        extra = {"operation": operation_name, "duration_ms": elapsed}
        if project_id:
            extra["project_id"] = project_id

        logger.info(
            f"⏱️ {operation_name} took {elapsed:.1f}ms",
            extra=extra
        )
```

**Usage**:
```python
with timer("DI Agent - Fetch state", str(project_id)):
    state_snapshot = get_state_snapshot(project_id)

with timer("DI Agent - Compute readiness", str(project_id)):
    readiness = compute_readiness(project_id)
```

**Impact**: Visibility into bottlenecks, enables data-driven optimization

---

### Phase 2: Parallelization (4-6 hours)

#### 3.4 Parallel Data Loading in Readiness Computation

**File**: `app/core/readiness/score.py`

**Current (Sequential)**:
```python
def _fetch_project_state(project_id: UUID) -> dict:
    vp_steps = list_vp_steps(project_id)              # 200ms
    features = list_features(project_id)              # 200ms
    personas = list_personas(project_id)              # 200ms
    strategic_context = get_strategic_context(project_id)  # 200ms
    signals_result = list_project_signals(project_id) # 200ms
    meetings = list_meetings(project_id)              # 200ms
    foundation = get_project_foundation(project_id)   # 200ms
    # Total: ~1400ms
```

**Optimized (Parallel with async/await)**:

**Step 1**: Make DB functions async (or create async wrappers)

```python
# Option 1: Make existing functions async
async def list_vp_steps_async(project_id: UUID) -> list[dict]:
    """Async version of list_vp_steps."""
    # Use async Supabase client or run_in_executor for sync calls
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, list_vp_steps, project_id)
```

**Step 2**: Parallelize with asyncio.gather

```python
async def _fetch_project_state_async(project_id: UUID) -> dict:
    """Fetch all project state in parallel."""

    # Launch all DB calls concurrently
    (
        vp_steps,
        features,
        personas,
        strategic_context,
        signals_result,
        meetings,
        foundation,
    ) = await asyncio.gather(
        list_vp_steps_async(project_id),
        list_features_async(project_id),
        list_personas_async(project_id),
        get_strategic_context_async(project_id),
        list_project_signals_async(project_id),
        list_meetings_async(project_id),
        get_project_foundation_async(project_id),
    )

    # Rest of function unchanged
    signals = signals_result.get("signals", []) if isinstance(signals_result, dict) else []
    # ... continue as before
```

**Impact**: Reduces from ~1400ms to ~200-300ms (7x speedup!)

**Limitation**: Requires async Supabase client or thread pool for sync→async conversion

---

#### 3.5 Parallel Data Loading in DI Agent

**File**: `app/agents/di_agent.py`

**Current (Sequential)**:
```python
state_snapshot = get_state_snapshot(project_id)      # 200ms
readiness = compute_readiness(project_id)            # 1400ms (now 300ms with Phase 2.1)
di_cache = get_di_cache(project_id)                  # 200ms
cache_valid = is_cache_valid(project_id)             # 400ms (refetches)
unanalyzed = get_unanalyzed_signals(project_id)      # 400ms (refetches)
# Total: ~2600ms (or ~1200ms with Phase 2.1)
```

**Optimized (Parallel + Data Passing)**:
```python
# Launch independent queries in parallel
(
    state_snapshot,
    readiness,
    di_cache,
) = await asyncio.gather(
    get_state_snapshot_async(project_id),
    compute_readiness_async(project_id),  # Already optimized in Phase 2.1
    get_di_cache_async(project_id),
)

# Now use fetched cache to avoid refetching
unanalyzed = get_unanalyzed_signals_from_cache(project_id, di_cache)
cache_valid = is_cache_valid_from_data(di_cache, unanalyzed)

# Total: ~300ms (parallel max) + minimal processing
```

**Impact**: Reduces from ~1200ms to ~300-400ms (3x speedup!)

---

### Phase 3: Caching (2-3 hours)

#### 3.6 Implement Readiness Caching

**Table**: `readiness_cache` (already exists in schema!)

**File**: `app/db/readiness_cache.py` (new file)

```python
"""Readiness cache database operations."""

from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Optional
from app.db.supabase_client import get_supabase
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache TTL: 5 minutes (balance between freshness and performance)
READINESS_CACHE_TTL_MINUTES = 5


def get_cached_readiness(project_id: UUID) -> Optional[dict]:
    """
    Get cached readiness if still valid.

    Returns None if:
    - Cache doesn't exist
    - Cache is older than TTL
    - cached_readiness_data is null
    """
    supabase = get_supabase()

    response = (
        supabase.table("readiness_cache")
        .select("cached_readiness_data, computed_at")
        .eq("project_id", str(project_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        logger.debug(f"Readiness cache miss (not found): {project_id}")
        return None

    cached_data = response.data.get("cached_readiness_data")
    computed_at_str = response.data.get("computed_at")

    if not cached_data:
        logger.debug(f"Readiness cache miss (null data): {project_id}")
        return None

    # Check if cache is stale
    if computed_at_str:
        try:
            from dateutil import parser as dateutil_parser
            computed_at = dateutil_parser.isoparse(computed_at_str)
            age = datetime.now(timezone.utc) - computed_at

            if age > timedelta(minutes=READINESS_CACHE_TTL_MINUTES):
                logger.debug(
                    f"Readiness cache miss (stale): {project_id} "
                    f"({age.total_seconds() / 60:.1f} min old)"
                )
                return None
        except Exception as e:
            logger.warning(f"Failed to parse computed_at: {e}")
            return None

    logger.debug(f"Readiness cache HIT: {project_id}")
    return cached_data


def set_cached_readiness(project_id: UUID, readiness_data: dict) -> None:
    """
    Cache readiness result.

    Upserts the cached_readiness_data and computed_at timestamp.
    """
    supabase = get_supabase()

    payload = {
        "project_id": str(project_id),
        "cached_readiness_data": readiness_data,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase.table("readiness_cache").upsert(
        payload,
        on_conflict="project_id",
    ).execute()

    logger.debug(f"Cached readiness for project {project_id}")


def invalidate_readiness_cache(project_id: UUID) -> None:
    """
    Invalidate readiness cache by setting cached_readiness_data to null.

    Called when entities change, foundation updates, etc.
    """
    supabase = get_supabase()

    supabase.table("readiness_cache").update(
        {"cached_readiness_data": None}
    ).eq("project_id", str(project_id)).execute()

    logger.debug(f"Invalidated readiness cache for project {project_id}")
```

**File**: `app/core/readiness/score.py` (update)

```python
def compute_readiness(project_id: UUID, use_cache: bool = True) -> ReadinessScore:
    """
    Compute readiness score, using cache if available and valid.

    Args:
        project_id: Project UUID
        use_cache: Whether to use cached readiness (default True)

    Returns:
        ReadinessScore with full breakdown
    """
    # Try cache first
    if use_cache:
        cached = get_cached_readiness(project_id)
        if cached:
            logger.info(f"Using cached readiness for project {project_id}")
            return ReadinessScore(**cached)

    logger.info(f"Computing fresh readiness for project {project_id}")

    # ... rest of existing computation logic ...

    # Cache the result before returning
    result_dict = result.model_dump()
    set_cached_readiness(project_id, result_dict)

    return result
```

**Invalidation Hooks** (add to entity mutation endpoints):

```python
# In app/api/features.py, personas.py, etc.
from app.db.readiness_cache import invalidate_readiness_cache

@router.post("/projects/{project_id}/features")
async def create_feature(...):
    # ... create feature ...

    # Invalidate readiness cache since entities changed
    invalidate_readiness_cache(project_id)

    return response
```

**Impact**:
- Cache hit: ~50-100ms (vs 300ms optimized, vs 1400ms unoptimized)
- Expected hit rate: 60-80% (entities don't change that often)
- Average savings: ~200ms per DI Agent call

---

### Phase 4: Database Optimization (2-3 hours)

#### 3.7 Add Database Indexes

**Migration**: `migrations/XXX_add_performance_indexes.sql`

```sql
-- Index on foreign keys for faster joins
CREATE INDEX IF NOT EXISTS idx_signals_project_id ON signals(project_id);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_features_project_id ON features(project_id);
CREATE INDEX IF NOT EXISTS idx_personas_project_id ON personas(project_id);
CREATE INDEX IF NOT EXISTS idx_vp_steps_project_id ON vp_steps(project_id);
CREATE INDEX IF NOT EXISTS idx_meetings_project_id ON meetings(project_id);

-- Index for signal filtering (unanalyzed signals)
CREATE INDEX IF NOT EXISTS idx_signals_project_created ON signals(project_id, created_at);

-- Index for cache lookups
CREATE INDEX IF NOT EXISTS idx_di_cache_project_id ON di_analysis_cache(project_id);
CREATE INDEX IF NOT EXISTS idx_readiness_cache_project_id ON readiness_cache(project_id);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_signals_project_authority ON signals(project_id, authority);
CREATE INDEX IF NOT EXISTS idx_features_project_confirmed ON features(project_id, confirmed);
```

**Impact**: 10-20% reduction in query time for large projects

---

#### 3.8 Use COUNT(*) for Entity Counts

**File**: `app/core/readiness/score.py`

**Before**:
```python
features = list_features(project_id)  # Fetches ALL feature data
confirmed_count = len([f for f in features if f.get("confirmed")])
total_count = len(features)
```

**After**:
```python
# Just get counts, not full entities
total_count = count_features(project_id)
confirmed_count = count_confirmed_features(project_id)
```

**New functions** in `app/db/features.py`:

```python
def count_features(project_id: UUID) -> int:
    """Get total feature count without fetching full data."""
    supabase = get_supabase()
    response = (
        supabase.table("features")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .execute()
    )
    return response.count or 0

def count_confirmed_features(project_id: UUID) -> int:
    """Get confirmed feature count without fetching full data."""
    supabase = get_supabase()
    response = (
        supabase.table("features")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("confirmed", True)
        .execute()
    )
    return response.count or 0
```

**Impact**: Saves data transfer when only counts are needed (~50-100ms for large entity lists)

---

## 4. Expected Performance Improvements

### Before Optimization

| Operation | Current Time | Target |
|-----------|-------------|--------|
| DI Agent invocation | ~4-6 seconds | < 5 seconds |
| Readiness computation | ~1.4 seconds | < 2 seconds |
| Foundation extraction | ~8-15 seconds | < 10 seconds |
| Cache hit rate | Unknown | > 80% |

### After Phase 1 (Quick Wins)

| Operation | Optimized Time | Improvement |
|-----------|---------------|-------------|
| DI Agent invocation | ~3-4 seconds | 33% faster |
| Readiness computation | ~1.4 seconds | (no change) |
| Cache fetches | -2 redundant calls | 40% fewer DB calls |

### After Phase 2 (Parallelization)

| Operation | Optimized Time | Improvement |
|-----------|---------------|-------------|
| DI Agent invocation | ~1.5-2 seconds | 60-70% faster |
| Readiness computation | ~300-400ms | 75-80% faster |

### After Phase 3 (Caching)

| Operation | Optimized Time (cache hit) | Improvement |
|-----------|---------------------------|-------------|
| DI Agent invocation | ~800ms-1.2s | 80-85% faster |
| Readiness computation | ~50-100ms | 95% faster |
| Cache hit rate | ~70-80% | ✅ Target met |

### After Phase 4 (Database Optimization)

| Operation | Final Time | vs Original |
|-----------|-----------|-------------|
| DI Agent invocation | ~700ms-1s (p50), ~1.5-2s (p95) | **3-4x faster** ✅ |
| Readiness computation | ~40-80ms (p50), ~300ms (p95) | **15-20x faster** ✅ |
| Foundation extraction | ~6-8s (with parallel signals) | **30% faster** ✅ |

---

## 5. Implementation Priority

### Must Do (Phases 1 & 2)
✅ **Priority 1**: Fix redundant cache fetches (400-600ms savings)
✅ **Priority 2**: Optimize signal filtering (100-300ms savings)
✅ **Priority 3**: Add timing instrumentation (visibility)
✅ **Priority 4**: Parallel data loading in readiness (1000ms+ savings)
✅ **Priority 5**: Parallel data loading in DI Agent (800ms+ savings)

### Should Do (Phase 3)
🎯 **Priority 6**: Implement readiness caching (200ms+ savings on cache hit)
🎯 **Priority 7**: Add cache invalidation hooks

### Nice to Have (Phase 4)
💡 **Priority 8**: Add database indexes (10-20% savings)
💡 **Priority 9**: Use COUNT(*) for entity counts (50-100ms savings)

---

## 6. Risks and Mitigation

### Risk 1: Async/Await Complexity
**Concern**: Converting sync DB calls to async increases complexity
**Mitigation**:
- Use `loop.run_in_executor()` for sync→async wrapper
- Keep sync functions, add `_async` versions alongside
- Gradually migrate, test thoroughly

### Risk 2: Cache Staleness
**Concern**: Cached readiness may be out of sync with reality
**Mitigation**:
- Short TTL (5 minutes)
- Invalidate on entity changes
- Always include `computed_at` timestamp
- Allow `use_cache=False` override for critical paths

### Risk 3: Supabase Connection Pool Limits
**Concern**: Parallel queries may exhaust connection pool
**Mitigation**:
- Use connection pooling (Supabase-py supports this)
- Limit parallelism to ~10 concurrent queries
- Monitor connection pool usage

### Risk 4: Database Load
**Concern**: More concurrent queries = higher DB load
**Mitigation**:
- Indexes reduce per-query cost
- Caching reduces total query volume
- Monitor database metrics (CPU, connections)
- Scale Supabase tier if needed

---

## 7. Monitoring and Metrics

### Key Metrics to Track

1. **Latency Percentiles** (p50, p95, p99):
   - DI Agent invocation time
   - Readiness computation time
   - Foundation extraction time

2. **Cache Performance**:
   - Readiness cache hit rate
   - DI cache validity rate
   - Cache invalidation frequency

3. **Database Performance**:
   - Query count per request
   - Average query duration
   - Connection pool utilization

4. **LLM Performance**:
   - Anthropic API latency (separate from DB)
   - Token usage
   - Streaming vs. non-streaming response times

### Logging Implementation

**File**: `app/core/metrics.py` (new)

```python
"""Performance metrics and logging."""

import time
from contextlib import contextmanager
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

class PerformanceTracker:
    """Track performance metrics for operations."""

    def __init__(self, operation: str, project_id: Optional[str] = None):
        self.operation = operation
        self.project_id = project_id
        self.start_time = None
        self.db_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def start(self):
        self.start_time = time.perf_counter()

    def end(self) -> float:
        """Return duration in milliseconds."""
        if not self.start_time:
            return 0
        elapsed_ms = (time.perf_counter() - self.start_time) * 1000

        extra = {
            "operation": self.operation,
            "duration_ms": elapsed_ms,
            "db_calls": self.db_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }
        if self.project_id:
            extra["project_id"] = self.project_id

        logger.info(
            f"⏱️ {self.operation}: {elapsed_ms:.1f}ms "
            f"(DB: {self.db_calls}, Cache: {self.cache_hits}H/{self.cache_misses}M)",
            extra=extra
        )

        return elapsed_ms

    def record_db_call(self):
        self.db_calls += 1

    def record_cache_hit(self):
        self.cache_hits += 1

    def record_cache_miss(self):
        self.cache_misses += 1


@contextmanager
def track_performance(operation: str, project_id: Optional[str] = None):
    """Context manager for tracking operation performance."""
    tracker = PerformanceTracker(operation, project_id)
    tracker.start()
    try:
        yield tracker
    finally:
        tracker.end()
```

**Usage**:
```python
from app.core.metrics import track_performance

async def invoke_di_agent(project_id: UUID, ...):
    with track_performance("DI Agent Invocation", str(project_id)) as perf:
        # Fetch state
        with timer("Fetch state"):
            state = await get_state_snapshot(project_id)
            perf.record_db_call()

        # Compute readiness (with caching)
        with timer("Compute readiness"):
            readiness = await compute_readiness(project_id)
            if readiness_was_cached:
                perf.record_cache_hit()
            else:
                perf.record_cache_miss()
                perf.record_db_call()
```

---

## 8. Next Steps

### Immediate (This Session)
- [x] Document performance analysis
- [ ] Implement Phase 1: Quick Wins
  - [ ] Fix redundant cache fetches
  - [ ] Optimize signal filtering
  - [ ] Add timing instrumentation

### This Week
- [ ] Implement Phase 2: Parallelization
  - [ ] Create async wrappers for DB functions
  - [ ] Parallelize readiness computation
  - [ ] Parallelize DI agent data loading

### Next Week
- [ ] Implement Phase 3: Caching
  - [ ] Readiness caching
  - [ ] Cache invalidation hooks
- [ ] Implement Phase 4: Database Optimization
  - [ ] Add indexes
  - [ ] Optimize entity count queries

### Ongoing
- [ ] Monitor metrics
- [ ] Tune cache TTLs based on usage
- [ ] Identify additional optimization opportunities

---

## Appendix: Code Snippets

### A. Async Wrapper Pattern

```python
import asyncio
from functools import wraps

def make_async(sync_func):
    """Convert sync function to async by running in executor."""
    @wraps(sync_func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)
    return async_wrapper

# Usage:
list_features_async = make_async(list_features)
list_personas_async = make_async(list_personas)
```

### B. Parallel Gather Pattern

```python
import asyncio

async def fetch_all_entities(project_id: UUID):
    """Fetch all entities in parallel."""
    features, personas, vp_steps = await asyncio.gather(
        list_features_async(project_id),
        list_personas_async(project_id),
        list_vp_steps_async(project_id),
    )
    return {"features": features, "personas": personas, "vp_steps": vp_steps}
```

### C. Cache Decorator Pattern

```python
from functools import wraps

def cached_readiness(ttl_minutes=5):
    """Decorator to cache readiness computation."""
    def decorator(func):
        @wraps(func)
        async def wrapper(project_id: UUID, use_cache=True):
            if use_cache:
                cached = get_cached_readiness(project_id)
                if cached:
                    return ReadinessScore(**cached)

            result = await func(project_id, use_cache=False)
            set_cached_readiness(project_id, result.model_dump())
            return result
        return wrapper
    return decorator

@cached_readiness(ttl_minutes=5)
async def compute_readiness(project_id: UUID, use_cache=True):
    # ... computation logic ...
    pass
```

---

**End of Performance Optimization Plan**
