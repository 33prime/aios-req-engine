"""
Chunk deduplication and reranking utilities.

Provides post-retrieval cleaning of vector search results:
1. Semantic deduplication (remove similar chunks)
2. Section-aware limits (max chunks per section type)
3. Diversity reranking (MMR algorithm)
"""

from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def deduplicate_chunks(
    chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
    max_per_section: int = 3,
    embedding_key: str = "embedding"
) -> List[Dict[str, Any]]:
    """
    Deduplicate retrieved chunks using semantic similarity.

    Strategy:
    1. Group by section_type (preserve diversity across sections)
    2. Within each section, deduplicate by embedding similarity
    3. Limit chunks per section type
    4. Return deduplicated list

    Args:
        chunks: List of chunk dictionaries with embeddings
        similarity_threshold: Cosine similarity threshold (0-1). Chunks above this are considered duplicates.
        max_per_section: Maximum chunks to keep per section type
        embedding_key: Key in chunk dict where embedding is stored

    Returns:
        Deduplicated list of chunks

    Example:
        >>> chunks = [
        ...     {"id": "1", "content": "...", "embedding": [...], "metadata": {"section_type": "features"}},
        ...     {"id": "2", "content": "...", "embedding": [...], "metadata": {"section_type": "features"}},
        ... ]
        >>> unique = deduplicate_chunks(chunks, similarity_threshold=0.85, max_per_section=2)
    """
    if not chunks:
        return []

    # Group by section type
    by_section = {}
    for chunk in chunks:
        section = chunk.get("metadata", {}).get("section_type", "unknown")
        if section not in by_section:
            by_section[section] = []
        by_section[section].append(chunk)

    deduplicated = []

    for section_type, section_chunks in by_section.items():
        # If only 1 chunk in section, keep it
        if len(section_chunks) == 1:
            deduplicated.extend(section_chunks)
            continue

        # Extract embeddings
        embeddings = []
        valid_chunks = []
        for chunk in section_chunks:
            emb = chunk.get(embedding_key)
            if emb is not None and isinstance(emb, (list, np.ndarray)):
                embeddings.append(emb)
                valid_chunks.append(chunk)

        # If no valid embeddings, just take first N
        if not embeddings:
            deduplicated.extend(section_chunks[:max_per_section])
            continue

        # If only one valid embedding, keep it
        if len(embeddings) == 1:
            deduplicated.extend(valid_chunks)
            continue

        # Compute pairwise similarity
        embeddings_matrix = np.array(embeddings)
        similarities = cosine_similarity(embeddings_matrix)

        # Greedy deduplication: keep chunks that are dissimilar
        kept_indices = [0]  # Always keep first chunk

        for i in range(1, len(valid_chunks)):
            # Check if this chunk is too similar to any kept chunk
            is_duplicate = False
            for kept_idx in kept_indices:
                if similarities[i][kept_idx] > similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                kept_indices.append(i)

            # Stop if we've hit max per section
            if len(kept_indices) >= max_per_section:
                break

        # Add kept chunks
        for idx in kept_indices:
            deduplicated.append(valid_chunks[idx])

    return deduplicated


def rerank_for_diversity(
    chunks: List[Dict[str, Any]],
    alpha: float = 0.7,
    embedding_key: str = "embedding",
    score_key: str = "similarity"
) -> List[Dict[str, Any]]:
    """
    Rerank chunks using Maximal Marginal Relevance (MMR).

    Balances relevance (similarity score) with diversity (dissimilarity to already selected).

    MMR = alpha * relevance - (1-alpha) * max_similarity_to_selected

    Args:
        chunks: List of chunk dictionaries with embeddings and scores
        alpha: Relevance vs diversity tradeoff (0=max diversity, 1=max relevance)
        embedding_key: Key in chunk dict where embedding is stored
        score_key: Key in chunk dict where relevance score is stored

    Returns:
        Reranked list of chunks

    Example:
        >>> chunks = [
        ...     {"id": "1", "similarity": 0.9, "embedding": [...]},
        ...     {"id": "2", "similarity": 0.8, "embedding": [...]},
        ... ]
        >>> reranked = rerank_for_diversity(chunks, alpha=0.7)
    """
    if len(chunks) <= 1:
        return chunks

    # Extract embeddings and scores
    embeddings = []
    scores = []
    valid_chunks = []

    for chunk in chunks:
        emb = chunk.get(embedding_key)
        score = chunk.get(score_key, 1.0)

        if emb is not None and isinstance(emb, (list, np.ndarray)):
            embeddings.append(emb)
            scores.append(score)
            valid_chunks.append(chunk)

    # If not enough valid chunks, return as-is
    if len(valid_chunks) <= 1:
        return chunks

    embeddings_matrix = np.array(embeddings)

    # Start with highest scoring chunk
    max_score_idx = scores.index(max(scores))
    selected_indices = [max_score_idx]
    remaining_indices = [i for i in range(len(valid_chunks)) if i != max_score_idx]

    # Iteratively select chunks that maximize MMR
    while remaining_indices:
        mmr_scores = []

        for idx in remaining_indices:
            # Relevance component (original similarity score)
            relevance = scores[idx]

            # Diversity component (max similarity to already selected)
            similarities_to_selected = [
                cosine_similarity([embeddings_matrix[idx]], [embeddings_matrix[sel_idx]])[0][0]
                for sel_idx in selected_indices
            ]
            max_sim = max(similarities_to_selected)

            # MMR score
            mmr = alpha * relevance - (1 - alpha) * max_sim
            mmr_scores.append((idx, mmr))

        # Select chunk with highest MMR
        best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

    # Return chunks in MMR order
    reranked = [valid_chunks[i] for i in selected_indices]

    # Add back any chunks without valid embeddings at the end
    invalid_chunks = [c for c in chunks if c not in valid_chunks]
    reranked.extend(invalid_chunks)

    return reranked


def deduplicate_by_id(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simple deduplication by chunk ID.

    Preserves order, keeping first occurrence of each unique chunk ID.

    Args:
        chunks: List of chunk dictionaries with 'id' field

    Returns:
        Deduplicated list (by ID)
    """
    seen = set()
    unique = []

    for chunk in chunks:
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen:
            unique.append(chunk)
            seen.add(chunk_id)

    return unique


def get_section_distribution(chunks: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get distribution of chunks by section type.

    Useful for debugging and understanding chunk diversity.

    Args:
        chunks: List of chunk dictionaries

    Returns:
        Dictionary mapping section_type to count

    Example:
        >>> chunks = [...]
        >>> dist = get_section_distribution(chunks)
        >>> print(dist)  # {"features_must_have": 5, "personas": 3, "risks": 2}
    """
    distribution = {}

    for chunk in chunks:
        section = chunk.get("metadata", {}).get("section_type", "unknown")
        distribution[section] = distribution.get(section, 0) + 1

    return distribution
