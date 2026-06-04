"""Cosine similarity calculator for function embeddings.

Operates entirely in-memory using numpy for vectorised dot products.
Edge count is bounded at N * top_n / 2 by only keeping top-N neighbours
per function and deduplicating by enforcing source_id < target_id.

Functions that have a description embedding but no code embedding are included
in the computation and scored on description similarity only.
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
    embeddings: list[tuple[str, list[float] | None, list[float] | None]],
    config: SimilarityConfig,
) -> list[SimilarityEdge]:
    """Compute SIMILAR_TO edges for all functions above the similarity threshold.

    Args:
        embeddings: List of ``(id, code_embedding, description_embedding)`` tuples.
            Either embedding may be ``None``. Functions with neither are skipped.
        config: Similarity thresholds and weights.

    Returns:
        Deduplicated list of ``SimilarityEdge`` objects where
        ``source_id < target_id``.
    """
    if len(embeddings) < 2:
        return []

    ids = [e[0] for e in embeddings]
    code_vecs = [e[1] for e in embeddings]
    desc_vecs = [e[2] for e in embeddings]
    n = len(ids)

    has_code = [v is not None for v in code_vecs]
    has_any_code = any(has_code)

    # Build code similarity matrix, substituting zero vectors for missing embeddings.
    # Rows/columns for functions without code are zeroed out after multiplication so
    # their spurious cosine scores (zero-vector dot products) never drive edge creation.
    if has_any_code:
        dim = next(len(v) for v in code_vecs if v is not None)
        code_matrix = np.array(
            [v if v is not None else [0.0] * dim for v in code_vecs],
            dtype=np.float32,
        )
        code_norm = _normalise(code_matrix)
        code_sim_matrix = code_norm @ code_norm.T
        has_code_arr = np.array(has_code)
        code_sim_matrix[~has_code_arr, :] = 0.0
        code_sim_matrix[:, ~has_code_arr] = 0.0
    else:
        code_sim_matrix = np.zeros((n, n), dtype=np.float32)

    # Pre-compute description similarity matrix if any embeddings exist.
    has_any_desc = any(v is not None for v in desc_vecs)
    if has_any_desc:
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

    for i in range(n):
        # Select top-N candidates using whichever signal is available for this function.
        if has_code[i]:
            selector = code_sim_matrix[i].copy()
        elif desc_sim_matrix is not None and desc_vecs[i] is not None:
            selector = desc_sim_matrix[i].copy()
        else:
            continue  # No signal available for this function

        selector[i] = -1.0
        top_indices = np.argpartition(selector, -min(config.top_n, n - 1))[-config.top_n:]

        for j in top_indices:
            j = int(j)
            if j == i:
                continue
            if ids[i] >= ids[j]:
                continue

            a_has_code = has_code[i]
            b_has_code = has_code[j]
            a_has_desc = desc_vecs[i] is not None
            b_has_desc = desc_vecs[j] is not None

            if a_has_code and b_has_code:
                # Normal path: both have code embeddings.
                code_sim = float(code_sim_matrix[i, j])
                if code_sim < config.threshold:
                    continue
                if desc_sim_matrix is not None and a_has_desc and b_has_desc:
                    desc_sim = float(desc_sim_matrix[i, j])
                    combined = config.code_weight * code_sim + config.description_weight * desc_sim
                else:
                    desc_sim = 0.0
                    combined = code_sim
            else:
                # At least one function lacks a code embedding — use description only.
                if desc_sim_matrix is None or not a_has_desc or not b_has_desc:
                    continue  # No usable signal for this pair
                code_sim = 0.0
                desc_sim = float(desc_sim_matrix[i, j])
                combined = desc_sim

            if combined < config.threshold:
                continue

            edges.append(SimilarityEdge(
                source_id=ids[i],
                target_id=ids[j],
                code_similarity=code_sim,
                description_similarity=desc_sim,
                combined_similarity=combined,
            ))

    return edges
