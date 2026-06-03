import math

from src.pipeline.contracts import SimilarityConfig
from src.pipeline.similarity import compute_similarity_edges


def _norm(v: list[float]) -> list[float]:
    mag = math.sqrt(sum(x * x for x in v))
    return [x / mag for x in v]


# Identical vectors → cosine similarity of 1.0
_V1 = _norm([1.0, 0.0, 0.0])
_V2 = _norm([1.0, 0.0, 0.0])
# Orthogonal vector → cosine similarity of 0.0
_V3 = _norm([0.0, 1.0, 0.0])


def test_identical_vectors_similarity_is_one():
    embs = [("a", _V1, None), ("b", _V2, None)]
    config = SimilarityConfig(threshold=0.9, top_n=10, code_weight=1.0, description_weight=0.0)
    edges = compute_similarity_edges(embs, config)
    assert len(edges) == 1
    assert abs(edges[0].combined_similarity - 1.0) < 1e-5


def test_orthogonal_vectors_produce_no_edges():
    embs = [("a", _V1, None), ("b", _V3, None)]
    config = SimilarityConfig(threshold=0.5, top_n=10, code_weight=1.0, description_weight=0.0)
    edges = compute_similarity_edges(embs, config)
    assert edges == []


def test_source_id_always_less_than_target_id():
    embs = [("z", _V1, None), ("a", _V2, None)]
    config = SimilarityConfig(threshold=0.9, top_n=10, code_weight=1.0, description_weight=0.0)
    edges = compute_similarity_edges(embs, config)
    for edge in edges:
        assert edge.source_id < edge.target_id


def test_no_self_edges():
    embs = [("a", _V1, None), ("b", _V3, None)]
    config = SimilarityConfig(threshold=0.0, top_n=10, code_weight=1.0, description_weight=0.0)
    edges = compute_similarity_edges(embs, config)
    for edge in edges:
        assert edge.source_id != edge.target_id


def test_weighted_combination():
    v_code = _norm([1.0, 0.0])
    v_desc = _norm([1.0, 0.0])
    # code similarity ≈ 1.0, desc similarity ≈ 1.0
    embs = [("a", v_code, v_desc), ("b", v_code, v_desc)]
    config = SimilarityConfig(threshold=0.5, top_n=10, code_weight=0.7, description_weight=0.3)
    edges = compute_similarity_edges(embs, config)
    assert len(edges) == 1
    # 0.7 * 1.0 + 0.3 * 1.0 = 1.0
    assert abs(edges[0].combined_similarity - 1.0) < 1e-4


def test_missing_description_embedding_uses_code_only():
    embs = [("a", _V1, None), ("b", _V2, None)]
    config = SimilarityConfig(threshold=0.5, top_n=10, code_weight=0.7, description_weight=0.3)
    edges = compute_similarity_edges(embs, config)
    assert len(edges) == 1
    # No desc embeddings → combined == code_sim
    assert abs(edges[0].combined_similarity - 1.0) < 1e-4


def test_fewer_than_two_returns_empty():
    assert compute_similarity_edges([], SimilarityConfig()) == []
    assert compute_similarity_edges([("a", _V1, None)], SimilarityConfig()) == []


def test_threshold_filters_low_similarity():
    v_high = _norm([1.0, 0.0, 0.0])
    v_low = _norm([0.5, 0.5, 0.707])  # ~0.5 similarity to v_high
    embs = [("a", v_high, None), ("b", v_low, None)]
    config = SimilarityConfig(threshold=0.99, top_n=10, code_weight=1.0, description_weight=0.0)
    edges = compute_similarity_edges(embs, config)
    assert edges == []
