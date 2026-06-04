import hashlib
import tempfile
from pathlib import Path

import pytest

from src.pipeline.contracts import PipelineConfig, Neo4jConfig, SimilarityConfig
from src.pipeline.extractor import FunctionExtractor, _record_id, _source_hash

_NEO4J = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="pw")
_SIM = SimilarityConfig()


def _make_config(repo_path: str) -> PipelineConfig:
    return PipelineConfig(
        repo_path=repo_path,
        repo_name="test-repo",
        supported_languages=["python"],
        ignore_paths=[".venv", "__pycache__"],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="qwen2.5-coder:7b",
        describer_model="qwen2.5-coder:7b",
        similarity=_SIM,
        neo4j=_NEO4J,
    )


def test_record_id_is_stable():
    id1 = _record_id("repo", "src/foo.py", "Bar.baz", 10)
    id2 = _record_id("repo", "src/foo.py", "Bar.baz", 10)
    assert id1 == id2
    assert len(id1) == 64   # sha256 hex digest


def test_record_id_differs_on_line_change():
    assert _record_id("repo", "f.py", "func", 1) != _record_id("repo", "f.py", "func", 2)


def test_source_hash():
    code = "def foo(): pass"
    expected = hashlib.sha256(code.encode("utf-8")).hexdigest()
    assert _source_hash(code) == expected


def test_extracts_top_level_function():
    src = "def greet(name):\n    return f'hello {name}'\n"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "greet.py").write_text(src)
        extractor = FunctionExtractor(_make_config(tmp))
        records = extractor.extract_all()

    assert len(records) == 1
    r = records[0]
    assert r.function_name == "greet"
    assert r.qualified_name == "greet"
    assert r.class_name is None
    assert r.start_line == 1
    assert r.language == "python"
    assert "def greet" in r.source_code


def test_extracts_method_with_class_name():
    src = (
        "class Greeter:\n"
        "    def hello(self):\n"
        "        return 'hello'\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "greeter.py").write_text(src)
        extractor = FunctionExtractor(_make_config(tmp))
        records = extractor.extract_all()

    assert len(records) == 1
    r = records[0]
    assert r.function_name == "hello"
    assert r.class_name == "Greeter"
    assert r.qualified_name == "Greeter.hello"


def test_extracts_multiple_functions():
    src = "def a(): pass\ndef b(): pass\ndef c(): pass\n"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "funcs.py").write_text(src)
        extractor = FunctionExtractor(_make_config(tmp))
        records = extractor.extract_all()

    assert len(records) == 3
    names = {r.function_name for r in records}
    assert names == {"a", "b", "c"}


def test_ignores_configured_paths():
    src = "def secret(): pass\n"
    with tempfile.TemporaryDirectory() as tmp:
        venv_dir = Path(tmp) / ".venv"
        venv_dir.mkdir()
        (venv_dir / "hidden.py").write_text(src)
        extractor = FunctionExtractor(_make_config(tmp))
        records = extractor.extract_all()

    assert records == []


def test_skips_unparseable_file():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "broken.py").write_bytes(b"\xff\xfe invalid utf-8 \x00")
        extractor = FunctionExtractor(_make_config(tmp))
        # Should not raise; just returns whatever tree-sitter can parse.
        records = extractor.extract_all()
        assert isinstance(records, list)
