import tempfile
from pathlib import Path

from src.pipeline.extraction.scanner import scan_repository


def _make_tree(root: Path, files: list[str]) -> None:
    for rel in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# content")


def test_returns_python_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, ["a.py", "b.py", "c.txt"])
        result = scan_repository(root, ["python"], [])
        names = [p.name for p in result]
        assert "a.py" in names
        assert "b.py" in names
        assert "c.txt" not in names


def test_ignores_configured_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, ["src/main.py", "node_modules/lib.py", ".venv/dep.py"])
        result = scan_repository(root, ["python"], ["node_modules", ".venv"])
        rel_paths = [str(p.relative_to(root)) for p in result]
        assert "src/main.py" in rel_paths
        assert not any("node_modules" in p for p in rel_paths)
        assert not any(".venv" in p for p in rel_paths)


def test_returns_sorted_paths():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, ["z.py", "a.py", "m.py"])
        result = scan_repository(root, ["python"], [])
        names = [p.name for p in result]
        assert names == sorted(names)


def test_typescript_extension_support():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, ["app.ts", "component.tsx", "readme.md"])
        result = scan_repository(root, ["typescript"], [])
        names = [p.name for p in result]
        assert "app.ts" in names
        assert "component.tsx" in names
        assert "readme.md" not in names


def test_ignores_multi_level_path():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_tree(root, [
            "apps/api/src/business/authBusiness.ts",
            "apps/api/src/dal/models/user.ts",
            "apps/api/src/dal/models/order.ts",
        ])
        result = scan_repository(root, ["typescript"], ["dal/models"])
        rel_paths = [str(p.relative_to(root)) for p in result]
        assert "apps/api/src/business/authBusiness.ts" in rel_paths
        assert not any("dal/models" in p for p in rel_paths)


def test_empty_repo_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        result = scan_repository(tmp, ["python"], [])
        assert result == []
