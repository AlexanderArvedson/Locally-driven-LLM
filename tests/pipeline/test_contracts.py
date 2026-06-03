import hashlib

from src.pipeline.contracts import FunctionRecord, SimilarityEdge


def _make_record(**kwargs) -> FunctionRecord:
    defaults = dict(
        id="abc",
        repo="repo",
        language="python",
        file_path="foo.py",
        function_name="foo",
        qualified_name="foo",
        class_name=None,
        start_line=1,
        end_line=5,
        source_code="def foo(): pass",
        source_hash=hashlib.sha256(b"def foo(): pass").hexdigest(),
    )
    defaults.update(kwargs)
    return FunctionRecord(**defaults)


def test_function_record_defaults():
    r = _make_record()
    assert r.is_deleted is False
    assert r.code_embedding is None
    assert r.description is None
    assert r.description_embedding is None


def test_function_record_id_is_stable():
    """Same inputs must always produce the same sha256 ID."""
    import hashlib
    key = "repo:/path/to/file.py:MyClass.my_method:42"
    expected = hashlib.sha256(key.encode("utf-8")).hexdigest()

    r = _make_record(
        id=expected,
        file_path="/path/to/file.py",
        qualified_name="MyClass.my_method",
        start_line=42,
    )
    assert r.id == expected


def test_similarity_edge_fields():
    edge = SimilarityEdge(
        source_id="aaa",
        target_id="bbb",
        code_similarity=0.9,
        description_similarity=0.8,
        combined_similarity=0.87,
    )
    assert edge.source_id < edge.target_id
    assert 0 <= edge.combined_similarity <= 1
