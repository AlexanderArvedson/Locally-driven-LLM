"""Cosine similarity calculator for function embeddings.

Operates entirely in-memory using numpy for vectorised dot products.
Edge count is bounded at N * top_n / 2 by only keeping top-N neighbours
per function and deduplicating by enforcing source_id < target_id.
"""

from __future__ import annotations

import numpy as np

from src.pipeline.contracts import SimilarityConfig, SimilarityEdge


def _normalise(vectors: np.ndarray) -> np.ndarray:
    """L2-normalise each row. Rows with zero norm are left as-is."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vectors / norms


def compute_similarity_edges(
    embeddings: list[tuple[str, list[float], list[float] | None]],
    config: SimilarityConfig,
) -> list[SimilarityEdge]:
    """Compute SIMILAR_TO edges for all functions above the similarity threshold.

    Args:
        embeddings: List of ``(id, code_embedding, description_embedding)`` tuples.
            ``description_embedding`` may be ``None``.
        config: Similarity thresholds and weights.

    Returns:
        Deduplicated list of ``SimilarityEdge`` objects where
        ``source_id < target_id``.
    """
    if len(embeddings) < 2:
        return []

    ids = [e[0] for e in embeddings]
    code_matrix = np.array([e[1] for e in embeddings], dtype=np.float32)
    code_norm = _normalise(code_matrix)

    # Full N×N cosine similarity via matrix multiplication.
    code_sim_matrix = code_norm @ code_norm.T

    # Pre-compute description similarity matrix if any embeddings exist.
    desc_vecs = [e[2] for e in embeddings]
    has_any_desc = any(v is not None for v in desc_vecs)
    if has_any_desc:
        # Replace missing description embeddings with zero vectors.
        dim = next(len(v) for v in desc_vecs if v is not None)
        desc_matrix = np.array(
            [v if v is not None else [0.0] * dim for v in desc_vecs],
            dtype=np.float32,
        )
        desc_norm = _normalise(desc_matrix)
        desc_sim_matrix: np.ndarray | None = desc_norm @ desc_norm.T
    else:
        desc_sim_matrix = None

    edges: list[SimilarityEdge] = []
    n = len(ids)

    for i in range(n):
        # Take top_n candidates by code similarity, excluding self.
        row = code_sim_matrix[i].copy()
        row[i] = -1.0   # exclude self
        top_indices = np.argpartition(row, -min(config.top_n, n - 1))[-config.top_n:]

        for j in top_indices:
            j = int(j)
            if j == i:
                continue

            code_sim = float(code_sim_matrix[i, j])
            if code_sim < config.threshold:
                continue

            # Enforce source_id < target_id to avoid duplicate edges.
            if ids[i] >= ids[j]:
                continue

            if desc_sim_matrix is not None and desc_vecs[i] is not None and desc_vecs[j] is not None:
                desc_sim = float(desc_sim_matrix[i, j])
                combined = config.code_weight * code_sim + config.description_weight * desc_sim
            else:
                desc_sim = 0.0
                combined = code_sim

            edges.append(SimilarityEdge(
                source_id=ids[i],
                target_id=ids[j],
                code_similarity=code_sim,
                description_similarity=desc_sim,
                combined_similarity=combined,
            ))

    return edges
