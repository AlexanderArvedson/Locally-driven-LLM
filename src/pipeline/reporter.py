"""Post-run report generator.

Queries Neo4j after a pipeline run and writes a markdown report summarising
the similarity graph: statistics, near-duplicates, most-connected functions,
and per-file edge counts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import LiteralString

from src.pipeline.contracts import Neo4jConfig
from src.pipeline.neo4j_store import Neo4jStore

# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

_Q_STATS: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
WITH count(f) AS total
OPTIONAL MATCH ()-[r:SIMILAR_TO]->()
RETURN total, count(r) AS edges
"""

_Q_TEST_COUNT: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false, isTest: true})
RETURN count(f) AS test_count
"""

_Q_NO_EDGES: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests) AND NOT (f)-[:SIMILAR_TO]-()
RETURN count(f) AS isolated
"""

_Q_TOP_PAIRS: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function)
WHERE (a.isTest = false OR $include_tests) AND (b.isTest = false OR $include_tests)
RETURN
  a.qualifiedName AS a_name,
  a.filePath      AS a_file,
  b.qualifiedName AS b_name,
  b.filePath      AS b_file,
  r.combinedSimilarity AS score
ORDER BY score DESC
LIMIT $limit
"""

_Q_MOST_CONNECTED: LiteralString = """
MATCH (f:Function {repo: $repo})-[r:SIMILAR_TO]-()
WHERE f.isTest = false OR $include_tests
RETURN
  f.qualifiedName AS name,
  f.filePath      AS file,
  count(r)        AS connections
ORDER BY connections DESC
LIMIT $limit
"""

_Q_PER_FILE: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
WITH f.filePath AS path, count(f) AS fn_count
OPTIONAL MATCH (a:Function {repo: $repo, filePath: path})-[r:SIMILAR_TO]-()
RETURN path, fn_count, count(r) AS edge_count
ORDER BY edge_count DESC
LIMIT $limit
"""

_Q_LANGUAGE_BREAKDOWN: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.language AS language, count(f) AS count
ORDER BY count DESC
"""


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

async def generate_report(
    neo4j_config: Neo4jConfig,
    repo_name: str,
    output_path: str | Path | None = None,
    top_n: int = 20,
    include_tests: bool = False,
) -> Path:
    """Query Neo4j and write a markdown report.

    Args:
        neo4j_config: Connection settings for Neo4j.
        repo_name: The repository name to report on.
        output_path: Where to write the report. Defaults to
            ``pipeline-report-<timestamp>.md`` in the current directory.
        top_n: How many items to show in each ranked section.

    Returns:
        Path to the written report file.
    """
    if output_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_path = Path(f"pipeline-report-{ts}.md")
    output_path = Path(output_path)

    store = Neo4jStore(neo4j_config)
    try:
        lines = await _build_report(store, repo_name, top_n, include_tests)
    finally:
        await store.close()

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


async def _build_report(store: Neo4jStore, repo: str, top_n: int, include_tests: bool = False) -> list[str]:
    db = store._config.database
    driver = store._driver

    async def run(query: LiteralString, **params):
        async with driver.session(database=db) as session:
            result = await session.run(query, repo=repo, **params)
            return await result.data()

    stats      = await run(_Q_STATS, include_tests=include_tests)
    test_count = await run(_Q_TEST_COUNT)
    no_edges   = await run(_Q_NO_EDGES, include_tests=include_tests)
    top_pairs  = await run(_Q_TOP_PAIRS, limit=top_n, include_tests=include_tests)
    connected  = await run(_Q_MOST_CONNECTED, limit=top_n, include_tests=include_tests)
    per_file   = await run(_Q_PER_FILE, limit=top_n, include_tests=include_tests)
    languages  = await run(_Q_LANGUAGE_BREAKDOWN, include_tests=include_tests)

    total      = stats[0]["total"] if stats else 0
    edges      = stats[0]["edges"] if stats else 0
    isolated   = no_edges[0]["isolated"] if no_edges else 0
    test_funcs = test_count[0]["test_count"] if test_count else 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# Pipeline Report — `{repo}`",
        f"",
        f"Generated: {now}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Production functions indexed | {total} |",
        f"| Test functions ({'included in' if include_tests else 'excluded from'} graph) | {test_funcs} |",
        f"| SIMILAR\\_TO edges | {edges} |",
        f"| Isolated functions (no edges) | {isolated} |",
        f"| Functions with at least one edge | {total - isolated} |",
        f"",
    ]

    if languages:
        lines += [
            f"## Language Breakdown",
            f"",
            f"| Language | Functions |",
            f"|---|---|",
        ]
        for row in languages:
            lines.append(f"| {row['language']} | {row['count']} |")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## Top {top_n} Most Similar Pairs",
        f"",
        f"Potential duplicates or shared logic.",
        f"",
        f"| Score | Function A | File A | Function B | File B |",
        f"|---|---|---|---|---|",
    ]
    for row in top_pairs:
        score = f"{row['score']:.3f}"
        lines.append(
            f"| {score} | `{row['a_name']}` | {row['a_file']} "
            f"| `{row['b_name']}` | {row['b_file']} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Top {top_n} Most Connected Functions",
        f"",
        f"Functions with the most similarity edges — likely utility or pattern code reused across the codebase.",
        f"",
        f"| Connections | Function | File |",
        f"|---|---|---|",
    ]
    for row in connected:
        lines.append(f"| {row['connections']} | `{row['name']}` | {row['file']} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Top {top_n} Files by Edge Count",
        f"",
        f"Files whose functions are most similar to functions in other files.",
        f"",
        f"| Edges | Functions | File |",
        f"|---|---|---|",
    ]
    for row in per_file:
        lines.append(f"| {row['edge_count']} | {row['fn_count']} | {row['path']} |")

    lines += ["", "---", ""]
    return lines
