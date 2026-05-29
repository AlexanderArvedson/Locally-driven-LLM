"""Graphify indexer — internal graph-building utility.

Provides `build_ast_graph`, which runs AST extraction on a repository and
writes `graph.json` to a given output directory. This module is an internal
helper; all graph lifecycle decisions (freshness, storage, mode) are handled
exclusively by `graph_resolver_node`.
"""

from __future__ import annotations

from pathlib import Path


def build_ast_graph(repo_path: str, graph_dir: Path) -> None:
    """Run AST-only graphify extraction and write graph.json to graph_dir."""
    from graphify.detect import detect
    from graphify.extract import collect_files, extract
    from graphify.build import build_from_json
    from graphify.cluster import cluster
    from graphify.export import to_json

    detected = detect(Path(repo_path))
    code_files: list[Path] = []
    for f in detected.get("files", {}).get("code", []):
        p = Path(f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])

    if not code_files:
        return

    # cache_root=graph_dir keeps all graphify cache files out of the target repo
    extraction = extract(code_files, cache_root=graph_dir)
    G = build_from_json(extraction)
    if G.number_of_nodes() == 0:
        return

    communities = cluster(G)
    to_json(G, communities, str(graph_dir / "graph.json"))
