import hashlib
import tempfile
from pathlib import Path

import pytest

from src.pipeline.contracts import PipelineConfig, Neo4jConfig, SimilarityConfig
from src.pipeline.extractor import FunctionExtractor, _record_id, _source_hash

_NEO4J = Neo4jConfig(uri="bolt://localhost:7687", database="neo4j", username="neo4j", password="pw")
_SIM = SimilarityConfig()


def _make_config(repo_path: str, languages: list[str] | None = None) -> PipelineConfig:
    return PipelineConfig(
        repo_path=repo_path,
        repo_name="test-repo",
        supported_languages=languages or ["python"],
        ignore_paths=[".venv", "__pycache__"],
        embedding_model="nomic-embed-text",
        embedding_url="http://localhost:11434",
        allow_gpu=False,
        chat_model="qwen2.5-coder:7b",
        describer_model="qwen2.5-coder:7b",
        similarity=_SIM,
        neo4j=_NEO4J,
    )


def _extract_ts(src: str, ext: str = ".ts") -> list:
    """Write *src* to a temp file with the given extension and extract records."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / f"code{ext}").write_text(src)
        extractor = FunctionExtractor(_make_config(tmp, languages=["typescript"]))
        return extractor.extract_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Python extraction
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TypeScript — named forms (resolved via _get_name_token)
# ---------------------------------------------------------------------------

def test_ts_named_function_declaration():
    records = _extract_ts("function greet(name: string): string {\n  return `hello ${name}`;\n}\n")
    assert len(records) == 1
    assert records[0].function_name == "greet"
    assert records[0].class_name is None


def test_ts_class_method_uses_property_identifier():
    # method_definition names are property_identifier, not identifier — previously broken
    src = "class Greeter {\n  hello(): string {\n    return 'hi';\n  }\n}\n"
    records = _extract_ts(src)
    assert len(records) == 1
    assert records[0].function_name == "hello"
    assert records[0].class_name == "Greeter"
    assert records[0].qualified_name == "Greeter.hello"


def test_ts_class_name_resolved_via_type_identifier():
    # class_declaration uses type_identifier, not identifier — previously broken
    src = "class MyService {\n  run(): void {\n    return;\n  }\n}\n"
    records = _extract_ts(src)
    assert records[0].class_name == "MyService"


def test_ts_private_class_method():
    src = "class Foo {\n  #init(): void {\n    return;\n  }\n}\n"
    records = _extract_ts(src)
    assert len(records) == 1
    assert records[0].function_name == "#init"
    assert records[0].class_name == "Foo"


# ---------------------------------------------------------------------------
# TypeScript — anonymous forms (resolved via _resolve_name_from_context)
# ---------------------------------------------------------------------------

def test_ts_arrow_in_variable_declarator():
    records = _extract_ts("const greet = (name: string) => `hello ${name}`;\n")
    assert len(records) == 1
    assert records[0].function_name == "greet"


def test_ts_class_field_arrow():
    src = "class Foo {\n  bar = () => {\n    return 42;\n  };\n}\n"
    records = _extract_ts(src)
    arrows = [r for r in records if r.function_name == "bar"]
    assert len(arrows) == 1
    assert arrows[0].class_name == "Foo"


def test_ts_object_literal_pair():
    src = "const obj = {\n  onClick: () => {\n    console.log('click');\n  },\n};\n"
    records = _extract_ts(src)
    assert any(r.function_name == "onClick" for r in records)


def test_ts_assignment_expression():
    src = "let handler: () => void;\nhandler = () => {\n  return;\n};\n"
    records = _extract_ts(src)
    assert any(r.function_name == "handler" for r in records)


def test_ts_member_assignment_expression():
    src = "const obj: any = {};\nobj.method = () => {\n  return;\n};\n"
    records = _extract_ts(src)
    # Rightmost segment of obj.method should be used
    assert any(r.function_name == "method" for r in records)


def test_ts_jsx_attribute_callback():
    src = (
        "const El = () => (\n"
        "  <button onClick={() => { console.log('x'); }}>click</button>\n"
        ");\n"
    )
    records = _extract_ts(src, ext=".tsx")
    names = {r.function_name for r in records}
    assert "onClick" in names


def test_ts_call_expression_single_arg():
    # One callback arg: forEach(fn) → callee name with no suffix
    src = "items.forEach((item) => { console.log(item); });\n"
    records = _extract_ts(src)
    assert any(r.function_name == "forEach" for r in records)


def test_ts_call_expression_multi_arg():
    # Multiple args: useEffect(fn, []) → callee name with positional suffix
    src = "useEffect(() => {\n  return;\n}, []);\n"
    records = _extract_ts(src)
    assert any(r.function_name == "useEffect$0" for r in records)


def test_ts_export_default_anonymous():
    src = "export default function() {\n  return 42;\n}\n"
    records = _extract_ts(src)
    assert len(records) == 1
    assert records[0].function_name == "default"


def test_ts_export_default_arrow():
    src = "export default () => {\n  return 42;\n};\n"
    records = _extract_ts(src)
    assert len(records) == 1
    assert records[0].function_name == "default"


def test_ts_truly_anonymous_falls_back():
    # Arrow returned from another function — no context to infer a name
    src = "function makeHandler() {\n  return () => {\n    return 1;\n  };\n}\n"
    records = _extract_ts(src)
    names = {r.function_name for r in records}
    assert "makeHandler" in names
    assert "<anonymous>" in names
