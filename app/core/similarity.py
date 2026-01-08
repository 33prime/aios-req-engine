"""
Unified Similarity Matching Module.

Provides centralized similarity detection for all entity types (features, personas, vp_steps).
Consolidates logic previously scattered across features.py and personas.py.

Strategies:
1. Exact match (after normalization)
2. Token set ratio (rapidfuzz) - handles word reordering
3. Partial ratio (rapidfuzz) - handles substrings
4. Weighted ratio (rapidfuzz) - general fuzzy matching
5. Key term overlap - semantic-ish matching via term extraction
6. Embedding similarity (optional) - vector-based for complex cases

Usage:
    from app.core.similarity import SimilarityMatcher, MatchResult

    matcher = SimilarityMatcher()

    # Find best match for a candidate
    result = matcher.find_best_match(
        candidate="AI-powered Transcript Engine",
        corpus=[
            {"id": "1", "name": "AI Engine for Transcript Analysis"},
            {"id": "2", "name": "User Dashboard"},
        ],
        text_field="name"
    )

    if result.is_match:
        print(f"Matched: {result.matched_item['name']} (score: {result.score})")
    else:
        print("No match found - should create new entity")
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


# Try to import rapidfuzz
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed - similarity matching will be limited")


class MatchStrategy(Enum):
    """Available matching strategies."""
    EXACT = "exact"
    TOKEN_SET = "token_set"
    PARTIAL = "partial"
    WRATIO = "wratio"
    KEY_TERMS = "key_terms"
    EMBEDDING = "embedding"


@dataclass
class MatchResult:
    """Result of a similarity match operation."""
    is_match: bool
    score: float
    strategy: MatchStrategy | None
    matched_item: dict | None = None
    matched_id: str | None = None
    all_candidates: list[dict] = field(default_factory=list)

    @property
    def should_create(self) -> bool:
        """Returns True if no match found and should create new entity."""
        return not self.is_match

    @property
    def should_update(self) -> bool:
        """Returns True if match found and should update existing entity."""
        return self.is_match


@dataclass
class ScoredCandidate:
    """A candidate with its similarity score."""
    item: dict
    score: float
    strategy: MatchStrategy


@dataclass
class ThresholdConfig:
    """Configurable thresholds for different strategies."""
    exact: float = 0.95
    token_set: float = 0.75
    partial: float = 0.80
    wratio: float = 0.75
    key_terms: float = 0.60
    embedding: float = 0.85

    # Below this score, always create new (no ambiguity)
    create_threshold: float = 0.50

    # Above this score, always update (no ambiguity)
    update_threshold: float = 0.85


# Default thresholds
DEFAULT_THRESHOLDS = ThresholdConfig()

# Entity-specific threshold overrides
ENTITY_THRESHOLDS = {
    "feature": ThresholdConfig(
        token_set=0.75,
        partial=0.80,
        key_terms=0.60,
    ),
    "persona": ThresholdConfig(
        token_set=0.75,
        partial=0.80,
        key_terms=0.55,  # Slightly lower for persona names
    ),
    "vp_step": ThresholdConfig(
        token_set=0.70,  # VP steps can have more variation
        partial=0.75,
        key_terms=0.55,
    ),
}

# Stop words for key term extraction (expanded list)
STOP_WORDS = {
    # Common English
    "a", "an", "the", "for", "and", "or", "of", "to", "in", "on", "with",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "must", "shall", "can", "that", "this", "these", "those", "it", "its",
    "as", "at", "by", "from", "into", "through", "during", "before", "after",

    # Tech/Feature common words
    "based", "powered", "driven", "enabled", "using", "via",
    "feature", "system", "module", "component", "service", "tool",
    "new", "add", "create", "update", "delete", "manage", "view",

    # Persona common words
    "manager", "lead", "senior", "junior", "head", "chief", "director",
    "user", "admin", "customer", "client", "team", "member",
}


class SimilarityMatcher:
    """
    Unified similarity matcher for entity deduplication.

    Provides multi-strategy matching with configurable thresholds.
    """

    def __init__(
        self,
        thresholds: ThresholdConfig | None = None,
        entity_type: str | None = None,
        custom_stop_words: set[str] | None = None,
    ):
        """
        Initialize the matcher.

        Args:
            thresholds: Custom threshold configuration
            entity_type: Entity type for automatic threshold selection
            custom_stop_words: Additional stop words to filter
        """
        if thresholds:
            self.thresholds = thresholds
        elif entity_type and entity_type in ENTITY_THRESHOLDS:
            self.thresholds = ENTITY_THRESHOLDS[entity_type]
        else:
            self.thresholds = DEFAULT_THRESHOLDS

        self.stop_words = STOP_WORDS | (custom_stop_words or set())

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        - Lowercase
        - Remove punctuation (except spaces)
        - Normalize whitespace
        """
        if not text:
            return ""

        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text

    def extract_key_terms(self, text: str) -> set[str]:
        """
        Extract key terms from text, filtering stop words.

        Useful for semantic-ish matching:
        "AI Engine for Transcript Analysis" → {"ai", "engine", "transcript", "analysis"}
        """
        words = self.normalize_text(text).split()
        return {w for w in words if w not in self.stop_words and len(w) > 2}

    def compute_similarity(
        self,
        text_a: str,
        text_b: str,
        strategies: list[MatchStrategy] | None = None,
    ) -> tuple[float, MatchStrategy]:
        """
        Compute similarity between two texts using multiple strategies.

        Returns the best score and the strategy that produced it.

        Args:
            text_a: First text
            text_b: Second text
            strategies: Strategies to use (default: all except embedding)

        Returns:
            Tuple of (best_score, strategy_used)
        """
        if not text_a or not text_b:
            return (0.0, MatchStrategy.EXACT)

        norm_a = self.normalize_text(text_a)
        norm_b = self.normalize_text(text_b)

        # Strategy 1: Exact match after normalization
        if norm_a == norm_b:
            return (1.0, MatchStrategy.EXACT)

        best_score = 0.0
        best_strategy = MatchStrategy.EXACT

        # Default strategies (all except embedding which requires vectors)
        if strategies is None:
            strategies = [
                MatchStrategy.TOKEN_SET,
                MatchStrategy.PARTIAL,
                MatchStrategy.WRATIO,
                MatchStrategy.KEY_TERMS,
            ]

        # RapidFuzz strategies
        if RAPIDFUZZ_AVAILABLE:
            if MatchStrategy.TOKEN_SET in strategies:
                score = fuzz.token_set_ratio(norm_a, norm_b) / 100.0
                if score > best_score:
                    best_score = score
                    best_strategy = MatchStrategy.TOKEN_SET

            if MatchStrategy.PARTIAL in strategies:
                score = fuzz.partial_ratio(norm_a, norm_b) / 100.0
                if score > best_score:
                    best_score = score
                    best_strategy = MatchStrategy.PARTIAL

            if MatchStrategy.WRATIO in strategies:
                score = fuzz.WRatio(norm_a, norm_b) / 100.0
                if score > best_score:
                    best_score = score
                    best_strategy = MatchStrategy.WRATIO

        # Key term overlap
        if MatchStrategy.KEY_TERMS in strategies:
            terms_a = self.extract_key_terms(text_a)
            terms_b = self.extract_key_terms(text_b)

            if terms_a and terms_b:
                intersection = terms_a & terms_b
                union = terms_a | terms_b
                jaccard = len(intersection) / len(union) if union else 0.0

                # Coverage boost
                coverage_a = len(intersection) / len(terms_a) if terms_a else 0
                coverage_b = len(intersection) / len(terms_b) if terms_b else 0
                boosted_score = (jaccard + max(coverage_a, coverage_b)) / 2

                if boosted_score > best_score:
                    best_score = boosted_score
                    best_strategy = MatchStrategy.KEY_TERMS

        return (best_score, best_strategy)

    def compute_embedding_similarity(
        self,
        embedding_a: list[float] | np.ndarray,
        embedding_b: list[float] | np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding_a: First embedding vector
            embedding_b: Second embedding vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            a = np.array(embedding_a).reshape(1, -1)
            b = np.array(embedding_b).reshape(1, -1)
            return float(cosine_similarity(a, b)[0][0])
        except Exception as e:
            logger.warning(f"Failed to compute embedding similarity: {e}")
            return 0.0

    def get_threshold_for_strategy(self, strategy: MatchStrategy) -> float:
        """Get the threshold for a given strategy."""
        thresholds = {
            MatchStrategy.EXACT: self.thresholds.exact,
            MatchStrategy.TOKEN_SET: self.thresholds.token_set,
            MatchStrategy.PARTIAL: self.thresholds.partial,
            MatchStrategy.WRATIO: self.thresholds.wratio,
            MatchStrategy.KEY_TERMS: self.thresholds.key_terms,
            MatchStrategy.EMBEDDING: self.thresholds.embedding,
        }
        return thresholds.get(strategy, 0.75)

    def is_match(self, score: float, strategy: MatchStrategy) -> bool:
        """Check if a score constitutes a match for a given strategy."""
        threshold = self.get_threshold_for_strategy(strategy)
        return score >= threshold

    def find_best_match(
        self,
        candidate: str,
        corpus: list[dict],
        text_field: str = "name",
        id_field: str = "id",
        strategies: list[MatchStrategy] | None = None,
    ) -> MatchResult:
        """
        Find the best matching item in a corpus for a candidate text.

        Args:
            candidate: Text to match
            corpus: List of items to search
            text_field: Field containing text to match against
            id_field: Field containing item ID
            strategies: Strategies to use

        Returns:
            MatchResult with best match or no match
        """
        if not candidate or not corpus:
            return MatchResult(
                is_match=False,
                score=0.0,
                strategy=None,
                all_candidates=[],
            )

        scored_candidates: list[ScoredCandidate] = []

        for item in corpus:
            item_text = item.get(text_field, "")
            if not item_text:
                continue

            score, strategy = self.compute_similarity(candidate, item_text, strategies)

            scored_candidates.append(ScoredCandidate(
                item=item,
                score=score,
                strategy=strategy,
            ))

        if not scored_candidates:
            return MatchResult(
                is_match=False,
                score=0.0,
                strategy=None,
                all_candidates=[],
            )

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        best = scored_candidates[0]

        # Check if best match passes threshold
        is_match = self.is_match(best.score, best.strategy)

        return MatchResult(
            is_match=is_match,
            score=best.score,
            strategy=best.strategy,
            matched_item=best.item if is_match else None,
            matched_id=best.item.get(id_field) if is_match else None,
            all_candidates=[
                {
                    "id": sc.item.get(id_field),
                    "text": sc.item.get(text_field),
                    "score": sc.score,
                    "strategy": sc.strategy.value,
                }
                for sc in scored_candidates[:5]  # Top 5 candidates
            ],
        )

    def find_similar_in_corpus(
        self,
        candidate: str,
        corpus: list[dict],
        text_field: str = "name",
        id_field: str = "id",
        min_score: float = 0.5,
        max_results: int = 5,
    ) -> list[ScoredCandidate]:
        """
        Find all similar items in corpus above a minimum score.

        Useful for finding related entities or detecting near-duplicates.

        Args:
            candidate: Text to match
            corpus: List of items to search
            text_field: Field containing text to match against
            id_field: Field containing item ID
            min_score: Minimum similarity score to include
            max_results: Maximum results to return

        Returns:
            List of ScoredCandidate sorted by score descending
        """
        if not candidate or not corpus:
            return []

        results: list[ScoredCandidate] = []

        for item in corpus:
            item_text = item.get(text_field, "")
            if not item_text:
                continue

            score, strategy = self.compute_similarity(candidate, item_text)

            if score >= min_score:
                results.append(ScoredCandidate(
                    item=item,
                    score=score,
                    strategy=strategy,
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:max_results]

    def batch_deduplicate(
        self,
        items: list[dict],
        text_field: str = "name",
        id_field: str = "id",
    ) -> tuple[list[dict], list[dict]]:
        """
        Deduplicate a batch of items, keeping the first occurrence.

        Args:
            items: List of items to deduplicate
            text_field: Field containing text to compare
            id_field: Field containing item ID

        Returns:
            Tuple of (unique_items, duplicates)
        """
        unique: list[dict] = []
        duplicates: list[dict] = []

        for item in items:
            item_text = item.get(text_field, "")
            if not item_text:
                unique.append(item)
                continue

            # Check against already accepted unique items
            match = self.find_best_match(
                candidate=item_text,
                corpus=unique,
                text_field=text_field,
                id_field=id_field,
            )

            if match.is_match:
                duplicates.append({
                    **item,
                    "_duplicate_of": match.matched_id,
                    "_similarity_score": match.score,
                })
            else:
                unique.append(item)

        return unique, duplicates


# Convenience functions for common use cases

def find_matching_feature(
    feature_name: str,
    existing_features: list[dict],
) -> MatchResult:
    """
    Find if a feature name matches any existing feature.

    Args:
        feature_name: Name of the new feature
        existing_features: List of existing feature dicts

    Returns:
        MatchResult indicating if match found
    """
    matcher = SimilarityMatcher(entity_type="feature")
    return matcher.find_best_match(
        candidate=feature_name,
        corpus=existing_features,
        text_field="name",
        id_field="id",
    )


def find_matching_persona(
    persona_name: str,
    existing_personas: list[dict],
) -> MatchResult:
    """
    Find if a persona name matches any existing persona.

    Args:
        persona_name: Name of the new persona
        existing_personas: List of existing persona dicts

    Returns:
        MatchResult indicating if match found
    """
    matcher = SimilarityMatcher(entity_type="persona")
    return matcher.find_best_match(
        candidate=persona_name,
        corpus=existing_personas,
        text_field="name",
        id_field="id",
    )


def find_matching_vp_step(
    step_name: str,
    existing_steps: list[dict],
) -> MatchResult:
    """
    Find if a VP step name matches any existing step.

    Args:
        step_name: Name of the new VP step
        existing_steps: List of existing VP step dicts

    Returns:
        MatchResult indicating if match found
    """
    matcher = SimilarityMatcher(entity_type="vp_step")
    return matcher.find_best_match(
        candidate=step_name,
        corpus=existing_steps,
        text_field="name",
        id_field="id",
    )


def should_create_or_update(
    candidate_name: str,
    existing_entities: list[dict],
    entity_type: str = "feature",
) -> tuple[str, MatchResult]:
    """
    Determine whether to create a new entity or update an existing one.

    Args:
        candidate_name: Name of the candidate entity
        existing_entities: List of existing entities
        entity_type: Type of entity (feature, persona, vp_step)

    Returns:
        Tuple of (action, match_result) where action is "create", "update", or "review"
    """
    matcher = SimilarityMatcher(entity_type=entity_type)
    result = matcher.find_best_match(
        candidate=candidate_name,
        corpus=existing_entities,
        text_field="name",
        id_field="id",
    )

    if result.score < matcher.thresholds.create_threshold:
        return ("create", result)
    elif result.score >= matcher.thresholds.update_threshold:
        return ("update", result)
    else:
        # Ambiguous - needs human review
        return ("review", result)
