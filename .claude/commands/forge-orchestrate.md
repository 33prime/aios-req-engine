# Forge Orchestrate — Intelligent Build Orchestrator

Scan the target project, discover remaining work, decompose into parallel streams with optimal model assignments and budget estimates, then generate execution commands the user can run in separate terminals.

## Arguments
$ARGUMENTS

If a path is provided, orchestrate that project directory.
If no arguments, orchestrate the current working directory.

## Steps

### Phase 1: Reconnaissance — Build Work Inventory

Determine the target project directory from $ARGUMENTS (default: cwd).

Scan these sources to build a complete inventory of remaining work:

1. **Plan files** — Look for `build-plan.md`, `TODO.md`, `ROADMAP.md`, `*.plan.md`, `PLAN.md`, `.forge/work-inventory.md`
2. **GitHub issues** — Run `gh issue list --state open --limit 50` (skip if `gh` unavailable or not a GitHub repo)
3. **CLAUDE.md + cortex memory** — Read `CLAUDE.md` and any memory files in `~/.claude/projects/*/memory/` for this project. Look for active priorities, known gaps, planned features.
4. **Git signals** — `git log --oneline -30` for recent activity. `git branch -a` for feature branches (feature branches = in-progress or planned work). `git stash list` for stashed work.
5. **Codebase gaps** — Scan source files for:
   - `TODO` and `FIXME` comments (group by file/area)
   - Stub functions (functions with `pass`, `...`, `raise NotImplementedError`, or empty bodies)
   - Empty files (created but not implemented)
   - Failing or skipped tests (`pytest --collect-only -q` or check for `@skip`, `xit(`, `.skip(`)
6. **Test results** — If a test runner is available, run it in collect-only/dry-run mode to identify test coverage gaps

Synthesize all sources into a work inventory table:

```
## Work Inventory

| # | Task | Source | Files | Complexity | Priority |
|---|------|--------|-------|-----------|----------|
| 1 | Implement user auth middleware | build-plan.md | 4 | high | P0 |
| 2 | Add pagination to list endpoints | GitHub #23 | 3 | medium | P1 |
| 3 | Write tests for billing module | TODO comments | 6 | medium | P1 |
| 4 | Fix date formatting in reports | FIXME:reports.py | 1 | low | P2 |
| ...
```

**Present this table to the user. Ask them to:**
- Confirm the inventory is complete (or add missing tasks)
- Adjust priorities (P0 = must do, P1 = should do, P2 = nice to have)
- Remove tasks they don't want included
- Set a scope: "all P0+P1" or "just P0" or specific task numbers

Wait for user confirmation before proceeding.

### Phase 2: Dependency Graph — Map and Group

Take the confirmed task list and build a dependency graph:

1. **Map dependencies** — For each task, determine:
   - What files does it create or modify?
   - What files does it read/depend on?
   - Does it create types, schemas, migrations, or contracts that other tasks consume?
   - Does it depend on another task's output being in place first?

2. **Assign file ownership** — Every source file that will be modified gets assigned to exactly one task. If two tasks need the same file, they must be in the same stream.

3. **Group into streams** — Apply these rules in order:
   - Tasks with file overlap → same stream
   - Tasks in the same domain → prefer same stream
   - Tasks with producer/consumer dependency → prefer same stream (reduces wait time)
   - Balance stream sizes (no stream should have >40% of total work)
   - Target 2–5 streams total

4. **Compute critical path** — Which stream must finish first? Which streams can run fully in parallel? Which have a wait-then-go dependency?

Present the result as an ASCII dependency graph:

```
## Stream Architecture

Stream 1: Auth System [Opus]          Stream 2: API Endpoints [Sonnet]
├── T1: Auth middleware               ├── T2: Pagination
├── T5: Session management            ├── T6: Search endpoint
└── T8: Auth tests                    └── T7: Filters
     │                                     │
     └──── Stream 2 starts after T1 ───────┘

Stream 3: Tests & Docs [Haiku]
├── T3: Billing tests
├── T4: Date fix
└── T9: API docs
(can start immediately, no dependencies)

File Ownership:
  Stream 1: src/auth/*, src/middleware/auth.py, tests/test_auth.py
  Stream 2: src/api/endpoints/*, src/api/pagination.py
  Stream 3: tests/test_billing.py, src/reports/format.py, docs/*

Critical Path: Stream 1 → Stream 2 (T1 must complete before Stream 2 starts)
```

**Ask the user to confirm or adjust stream grouping.** They may want to move tasks between streams or change the dependency structure.

### Phase 3: Model Assignment

For each stream, evaluate the tasks and assign the optimal Claude model.

**Heuristics per task:**
- **Opus signals**: Architectural decisions required, 10+ files touched, spans 3+ directories, security-critical logic, no existing pattern to follow, complex state management, novel integration
- **Sonnet signals**: Standard feature implementation, 3–9 files, following established patterns, API endpoints, UI components, CRUD operations, moderate refactoring
- **Haiku signals**: Writing tests for existing code, documentation, boilerplate generation, config files, type definitions, ≤3 files, clear template to follow

**Stream assignment rule**: The stream gets the highest model needed by any task within it. (Claude CLI uses one model per session.)

Present assignments with reasoning:

```
## Model Assignments

| Stream | Model | Reason |
|--------|-------|--------|
| 1: Auth System | Opus | T1 requires architectural decisions (middleware design, session strategy), security-critical, 8 files across 3 dirs |
| 2: API Endpoints | Sonnet | Standard CRUD patterns, following existing endpoint structure, 6 files |
| 3: Tests & Docs | Haiku | All tasks have clear templates, mechanical test writing, ≤3 files each |
```

**Allow the user to override.** They might know that a "simple-looking" task is actually complex, or that an Opus task has enough prior art to run on Sonnet.

### Phase 4: Budget Estimation

Estimate cost per stream using token-based calculation.

**Per task, estimate:**
```
complexity → (iterations, context_tokens, output_tokens)
  low    → (3,  20_000,  4_000)
  medium → (8,  40_000,  8_000)
  high   → (15, 80_000, 12_000)
```

**Calculate cost per task:**
```
input_cost  = iterations × context_tokens × (model_input_rate / 1_000_000) × 0.40  # 60% cache discount
output_cost = iterations × output_tokens  × (model_output_rate / 1_000_000)
task_cost   = input_cost + output_cost
```

**Model rates (per 1M tokens):**
| Model | Input | Output |
|-------|-------|--------|
| Opus | $15.00 | $75.00 |
| Sonnet | $3.00 | $15.00 |
| Haiku | $0.80 | $4.00 |

**Apply safety factors:**
- Stream subtotal × 1.5 = conservative estimate
- Conservative × 1.2 = recommended `--max-budget-usd`

Present the budget breakdown:

```
## Budget Estimate

| Stream | Model | Tasks | Optimistic | Conservative | Recommended --max-budget-usd |
|--------|-------|-------|-----------|-------------|-------------------------------|
| 1: Auth | Opus | 3 | $4.20 | $6.30 | $7.56 |
| 2: API | Sonnet | 3 | $0.85 | $1.28 | $1.53 |
| 3: Tests | Haiku | 3 | $0.12 | $0.18 | $0.22 |
| **Total** | | **9** | **$5.17** | **$7.76** | **$9.31** |

Estimated wall-clock time: ~25 minutes (Stream 1 critical path: ~20 min, then Stream 2: ~5 min)
Stream 3 runs in parallel from the start.
```

**This is a confirmation gate. Explicitly ask:**
> "The estimated total cost is $5.17–$7.76 with a recommended budget cap of $9.31. Do you want to proceed? You can adjust stream models or remove tasks to reduce cost."

Wait for explicit user confirmation before proceeding to Phase 5.

### Phase 5: Execution Setup — Generate the Plan

Create the `.forge/` orchestration directory with all necessary files.

**1. Create `.forge/orchestrator.toml`:**
```toml
[orchestration]
created = "YYYY-MM-DDTHH:MM:SS"
target = "/path/to/project"
total_streams = 3
total_tasks = 9
estimated_cost_optimistic = 5.17
estimated_cost_conservative = 7.76

[[streams]]
id = 1
name = "Auth System"
model = "opus"
max_budget_usd = 7.56
status = "pending"
depends_on = []
tasks = ["T1", "T5", "T8"]
files = ["src/auth/*", "src/middleware/auth.py", "tests/test_auth.py"]

[[streams]]
id = 2
name = "API Endpoints"
model = "sonnet"
max_budget_usd = 1.53
status = "pending"
depends_on = [1]
tasks = ["T2", "T6", "T7"]
files = ["src/api/endpoints/*", "src/api/pagination.py"]

# ...
```

**2. Create `work-inventory.md`** with the full task details from Phase 1.

**3. Create per-stream plan files** (`stream-1-plan.md`, etc.):
```markdown
# Stream 1: Auth System

Model: Opus | Budget: $7.56 | Dependencies: none (start immediately)

## File Ownership
You have EXCLUSIVE write access to these files:
- src/auth/*
- src/middleware/auth.py
- tests/test_auth.py

Do NOT modify any files outside this list.

## Tasks

- [ ] T1: Implement auth middleware
  - Create JWT validation middleware in src/middleware/auth.py
  - Add route protection decorators
  - Files: src/middleware/auth.py, src/auth/jwt.py

- [ ] T5: Session management
  - ...

- [ ] T8: Auth tests
  - ...

## Completion
When all tasks are checked off, create a commit with message:
"feat(auth): implement authentication system [stream-1]"
```

**4. Create `progress.md`:**
```markdown
# Orchestration Progress

| Stream | Status | Tasks Done | Last Updated |
|--------|--------|-----------|-------------|
| 1: Auth | pending | 0/3 | — |
| 2: API | blocked (waiting on Stream 1) | 0/3 | — |
| 3: Tests | pending | 0/3 | — |
```

**5. Generate terminal commands.** Output the commands the user will run:

```
## Execution Commands

### Setup worktrees
git worktree add .forge/worktrees/stream-1 -b orchestrate/stream-1
git worktree add .forge/worktrees/stream-2 -b orchestrate/stream-2
git worktree add .forge/worktrees/stream-3 -b orchestrate/stream-3

### Copy orchestration files to each worktree
cp .forge/stream-1-plan.md .forge/worktrees/stream-1/.forge/
cp .forge/stream-2-plan.md .forge/worktrees/stream-2/.forge/
cp .forge/stream-3-plan.md .forge/worktrees/stream-3/.forge/

### Start streams (each in a separate terminal)

# Terminal 1 — Stream 1: Auth System [Opus] (start immediately)
cd .forge/worktrees/stream-1
claude --model opus --max-budget-usd 7.56 -p "Read .forge/stream-1-plan.md and execute all tasks. Follow file ownership constraints strictly."

# Terminal 2 — Stream 3: Tests & Docs [Haiku] (start immediately)
cd .forge/worktrees/stream-3
claude --model haiku --max-budget-usd 0.22 -p "Read .forge/stream-3-plan.md and execute all tasks. Follow file ownership constraints strictly."

# Terminal 3 — Stream 2: API Endpoints [Sonnet] (start AFTER Stream 1 completes)
cd .forge/worktrees/stream-2
claude --model sonnet --max-budget-usd 1.53 -p "Read .forge/stream-2-plan.md and execute all tasks. Follow file ownership constraints strictly."

### Monitor progress
watch -n 10 'for d in .forge/worktrees/stream-*/; do echo "=== $(basename $d) ==="; grep -c "\\[x\\]" "$d/.forge/"*-plan.md 2>/dev/null; done'
```

### Phase 6: Merge Strategy

After all streams complete, the user needs to merge everything back. Generate the merge plan:

```
## Merge Strategy

### Merge order (respects dependency graph)
1. Merge stream-1 (Auth) into main first — other streams may depend on its artifacts
2. Merge stream-3 (Tests) — no dependencies, order doesn't matter
3. Merge stream-2 (API) last — depends on stream-1's types/middleware

### Commands
git checkout main

# Merge stream 1
git merge orchestrate/stream-1 --no-ff -m "feat(auth): implement authentication system"

# Merge stream 3
git merge orchestrate/stream-3 --no-ff -m "test: add billing tests and fix date formatting"

# Merge stream 2
git merge orchestrate/stream-2 --no-ff -m "feat(api): add pagination, search, and filters"

### Integration verification
# After all merges, run full test suite
[project test command]

# If integration issues arise, run a Sonnet fixup pass:
claude --model sonnet -p "Run the full test suite. Fix any failures caused by merging the orchestration streams. The merge combined: auth system, API endpoints, and test additions."

### Cleanup
git worktree remove .forge/worktrees/stream-1
git worktree remove .forge/worktrees/stream-2
git worktree remove .forge/worktrees/stream-3
git branch -d orchestrate/stream-1 orchestrate/stream-2 orchestrate/stream-3
```

## Key Principles

- **Plan, don't execute.** You generate commands. The user runs them. This preserves auth context, gives full visibility, and makes debugging straightforward.
- **Exclusive file ownership eliminates merge conflicts.** This is non-negotiable. If two streams need the same file, restructure.
- **Conservative budgets.** Underestimating and hitting a ceiling mid-task is far worse than overestimating and spending 80%.
- **User confirmation gates.** Phases 1, 2, 3, and 4 each end with user confirmation. Never auto-advance past a gate.
- **Domain grouping over file-type grouping.** Keep each stream's context tight.
