"""Post-run report generator.

Queries Neo4j after a pipeline run and writes a structured markdown report:
embedding integrity, graph health, similarity distribution, duplication
clusters, heuristic flags, per-file coupling, and a machine-readable JSON
footer. All logic is deterministic — no LLM usage.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, LiteralString
from zoneinfo import ZoneInfo

from src.pipeline.contracts import Neo4jConfig, PipelineConfig, ReporterConfig
from src.pipeline.neo4j_store import Neo4jStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIPELINE_VERSION: Final[str] = "2.0"

# ---------------------------------------------------------------------------
# Queries — existing
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

_Q_LANGUAGE_BREAKDOWN: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.language AS language, count(f) AS count
ORDER BY count DESC
"""

# ---------------------------------------------------------------------------
# Queries — new
# ---------------------------------------------------------------------------

_Q_EMBEDDING_COVERAGE: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.codeEmbeddingStatus AS status, count(f) AS cnt
"""

_Q_DESCRIPTION_COVERAGE: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.descriptionStatus AS status, count(f) AS cnt
"""

_Q_EMBEDDING_FAILURES: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND (f.codeEmbeddingStatus IN ['timeout', 'context_overflow', 'error']
    OR f.descriptionStatus IN ['timeout', 'invalid_json', 'error'])
RETURN f.qualifiedName AS name, f.filePath AS file,
       f.codeEmbeddingStatus AS code_status,
       f.descriptionStatus AS desc_status
ORDER BY f.filePath
LIMIT $limit
"""

_Q_INTRA_INTER_EDGES: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE a.isTest = false OR $include_tests
RETURN
  sum(CASE WHEN a.filePath = b.filePath THEN 1 ELSE 0 END) AS intra,
  sum(CASE WHEN a.filePath <> b.filePath THEN 1 ELSE 0 END) AS inter
"""

_Q_SIMILARITY_DISTRIBUTION: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE a.isTest = false OR $include_tests
RETURN
  sum(CASE WHEN r.combinedSimilarity > $bin_high THEN 1 ELSE 0 END) AS gt_high,
  sum(CASE WHEN r.combinedSimilarity > $bin_mid AND r.combinedSimilarity <= $bin_high THEN 1 ELSE 0 END) AS b_mid_high,
  sum(CASE WHEN r.combinedSimilarity > $bin_low AND r.combinedSimilarity <= $bin_mid THEN 1 ELSE 0 END) AS b_low_mid,
  sum(CASE WHEN r.combinedSimilarity <= $bin_low THEN 1 ELSE 0 END) AS lt_low
"""

_Q_PER_FILE_INTER: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
WITH f.filePath AS path, count(f) AS fn_count
OPTIONAL MATCH (a:Function {repo: $repo, filePath: path})-[r:SIMILAR_TO]-(b:Function)
RETURN path, fn_count,
  count(r) AS edge_count,
  sum(CASE WHEN b.filePath <> path THEN 1 ELSE 0 END) AS inter_edges
ORDER BY edge_count DESC
LIMIT $limit
"""

_Q_CLUSTER_EDGES: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE r.combinedSimilarity >= $threshold
  AND (a.isTest = false OR $include_tests)
RETURN
  a.qualifiedName AS a_name, a.filePath AS a_file,
  b.qualifiedName AS b_name, b.filePath AS b_file,
  r.combinedSimilarity AS score
"""

_Q_TEST_POLLUTION: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]-(b:Function {repo: $repo})
WHERE a.isTest = true AND b.isTest = false
RETURN count(r) AS cross_edges
"""

# ---------------------------------------------------------------------------
# Clustering (Python-side BFS over edges retrieved from Neo4j)
# ---------------------------------------------------------------------------

def _compute_clusters(edges: list[dict]) -> list[dict]:
    """Build connected components from similarity edges via BFS.

    Each node is identified by its qualifiedName. Returns clusters sorted by
    size descending, each containing id, size, max_score, avg_score,
    files_involved, representative (highest-degree node), and nodes list.
    """
    if not edges:
        return []

    adj: dict[str, set[str]] = defaultdict(set)
    node_file: dict[str, str] = {}
    edge_scores: dict[tuple[str, str], float] = {}

    for row in edges:
        a, b = row["a_name"], row["b_name"]
        adj[a].add(b)
        adj[b].add(a)
        node_file[a] = row["a_file"]
        node_file[b] = row["b_file"]
        key = (min(a, b), max(a, b))
        edge_scores[key] = max(edge_scores.get(key, 0.0), row["score"])

    visited: set[str] = set()
    clusters: list[dict] = []

    for start in list(adj.keys()):
        if start in visited:
            continue
        component: list[str] = []
        queue: deque[str] = deque([start])
        visited.add(start)
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        if len(component) < 2:
            continue

        component_set = set(component)
        seen_keys: set[tuple[str, str]] = set()
        dedup_scores: list[float] = []
        for u in component:
            for v in adj[u]:
                if v in component_set:
                    key = (min(u, v), max(u, v))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        dedup_scores.append(edge_scores.get(key, 0.0))

        representative = max(component, key=lambda n: len(adj[n]))
        clusters.append({
            "size": len(component),
            "max_score": max(dedup_scores) if dedup_scores else 0.0,
            "avg_score": sum(dedup_scores) / len(dedup_scores) if dedup_scores else 0.0,
            "files_involved": sorted({node_file[n] for n in component}),
            "representative": representative,
            "nodes": component,
        })

    clusters.sort(key=lambda c: c["size"], reverse=True)
    for i, c in enumerate(clusters):
        c["id"] = i + 1
    return clusters


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

async def generate_report(
    neo4j_config: Neo4jConfig,
    repo_name: str,
    output_dir: str | Path | None = None,
    include_tests: bool = False,
    pipeline_config: PipelineConfig | None = None,
    loc_filtered: int | None = None,
) -> Path:
    """Query Neo4j and write a report directory containing report.md and report.json.

    Args:
        neo4j_config: Connection settings for Neo4j.
        repo_name: The repository name to report on.
        output_dir: Directory to write the two report files into. Defaults to
            ``run_reports/<timestamp>/`` relative to the current working directory.
            Created automatically if it does not exist.
        include_tests: Whether to include test functions in graph stats.
        pipeline_config: Full pipeline config for metadata and reporter
            thresholds. When None, defaults from ReporterConfig are used
            and model name is shown as "N/A".

    Returns:
        Path to the generated report.md file.
    """
    reporter_cfg = pipeline_config.reporter if pipeline_config else ReporterConfig()
    ts = datetime.now(ZoneInfo(reporter_cfg.timezone)).strftime("%Y%m%d-%H%M%S")
    if output_dir is None:
        output_dir = Path("run_reports") / ts
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    store = Neo4jStore(neo4j_config)
    try:
        lines, export = await _build_report(store, repo_name, include_tests, pipeline_config, loc_filtered)
    finally:
        await store.close()

    md_path = output_dir / f"report_{ts}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    (output_dir / f"report_{ts}.json").write_text(json.dumps(export, indent=2), encoding="utf-8")
    return md_path


async def _build_report(
    store: Neo4jStore,
    repo: str,
    include_tests: bool,
    pipeline_config: PipelineConfig | None,
    loc_filtered: int | None = None,
) -> tuple[list[str], dict]:
    db = store._config.database
    driver = store._driver

    reporter_cfg = pipeline_config.reporter if pipeline_config else ReporterConfig()
    top_n = reporter_cfg.top_n

    async def run(query: LiteralString, **params):
        async with driver.session(database=db) as session:
            result = await session.run(query, repo=repo, **params)
            return await result.data()

    # Run all queries
    stats          = await run(_Q_STATS,                   include_tests=include_tests)
    test_count     = await run(_Q_TEST_COUNT)
    no_edges       = await run(_Q_NO_EDGES,                include_tests=include_tests)
    top_pairs      = await run(_Q_TOP_PAIRS,               limit=top_n, include_tests=include_tests)
    connected      = await run(_Q_MOST_CONNECTED,          limit=top_n, include_tests=include_tests)
    languages      = await run(_Q_LANGUAGE_BREAKDOWN,      include_tests=include_tests)
    embed_cov      = await run(_Q_EMBEDDING_COVERAGE,      include_tests=include_tests)
    desc_cov       = await run(_Q_DESCRIPTION_COVERAGE,    include_tests=include_tests)
    embed_failures = await run(_Q_EMBEDDING_FAILURES,      limit=reporter_cfg.max_embedding_failures, include_tests=include_tests)
    intra_inter    = await run(_Q_INTRA_INTER_EDGES,       include_tests=include_tests)
    sim_dist       = await run(_Q_SIMILARITY_DISTRIBUTION,
                               bin_high=reporter_cfg.sim_dist_bin_high,
                               bin_mid=reporter_cfg.sim_dist_bin_mid,
                               bin_low=reporter_cfg.sim_dist_bin_low,
                               include_tests=include_tests)
    per_file       = await run(_Q_PER_FILE_INTER,          limit=top_n, include_tests=include_tests)
    cluster_edges  = await run(_Q_CLUSTER_EDGES,           threshold=reporter_cfg.cluster_threshold, include_tests=include_tests)
    test_pollution = await run(_Q_TEST_POLLUTION) if include_tests else [{"cross_edges": 0}]

    # Scalar extraction
    total       = stats[0]["total"] if stats else 0
    edges       = stats[0]["edges"] if stats else 0
    isolated    = no_edges[0]["isolated"] if no_edges else 0
    test_funcs  = test_count[0]["test_count"] if test_count else 0
    intra       = intra_inter[0]["intra"] if intra_inter else 0
    inter       = intra_inter[0]["inter"] if intra_inter else 0
    cross_edges = test_pollution[0]["cross_edges"] if test_pollution else 0

    density      = round(edges / total, 4) if total > 0 else 0.0
    isolated_pct = round(100 * isolated / total, 1) if total > 0 else 0.0

    gt_high   = sim_dist[0]["gt_high"]   if sim_dist else 0
    b_mid_high = sim_dist[0]["b_mid_high"] if sim_dist else 0
    b_low_mid  = sim_dist[0]["b_low_mid"]  if sim_dist else 0
    lt_low     = sim_dist[0]["lt_low"]     if sim_dist else 0

    # Embedding status bucketing
    embed_by_status: dict[str, int] = defaultdict(int)
    for row in embed_cov:
        embed_by_status[row["status"] or "null"] += row["cnt"]

    desc_by_status: dict[str, int] = defaultdict(int)
    for row in desc_cov:
        desc_by_status[row["status"] or "null"] += row["cnt"]

    embed_ok       = embed_by_status.get("ok", 0)
    embed_overflow = embed_by_status.get("context_overflow", 0)
    embed_timeout  = embed_by_status.get("timeout", 0)
    embed_error    = embed_by_status.get("error", 0)
    embed_skipped  = embed_by_status.get("skipped", 0)
    embed_unchanged = embed_by_status.get("null", 0)
    embed_failed   = embed_overflow + embed_timeout + embed_error

    desc_ok      = desc_by_status.get("ok", 0)
    desc_invalid = desc_by_status.get("invalid_json", 0)
    desc_timeout = desc_by_status.get("timeout", 0)
    desc_error   = desc_by_status.get("error", 0)
    desc_skipped = desc_by_status.get("skipped", 0)

    clusters = _compute_clusters(cluster_edges)

    tz = ZoneInfo(reporter_cfg.timezone)
    now_dt = datetime.now(tz)
    tz_abbr = now_dt.strftime("%Z") or reporter_cfg.timezone
    now = now_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")
    embed_model = pipeline_config.embedding_model if pipeline_config else "N/A"

    lines: list[str] = []

    # -----------------------------------------------------------------------
    # Section 1 — Metadata
    # -----------------------------------------------------------------------
    min_loc = pipeline_config.limits.min_loc_threshold if pipeline_config else 0

    lines += [
        f"# Pipeline Report — `{repo}`",
        "",
        "## Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Repository | `{repo}` |",
        f"| Generated ({reporter_cfg.timezone}) | {now} |",
        f"| Neo4j database | `{db}` |",
        f"| Pipeline version | {PIPELINE_VERSION} |",
        f"| Embedding model | `{embed_model}` |",
    ]
    if min_loc > 0:
        lines.append(f"| Min LOC threshold | {min_loc} |")
    lines += [
        "",
        "---",
        "",
    ]

    # -----------------------------------------------------------------------
    # Section 2 — Embedding Integrity
    # -----------------------------------------------------------------------
    lines += [
        "## Embedding Integrity",
        "",
        "### Code Embedding Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| ok | {embed_ok} |",
        f"| context\\_overflow | {embed_overflow} |",
        f"| timeout | {embed_timeout} |",
        f"| error | {embed_error} |",
        f"| skipped | {embed_skipped} |",
        f"| unchanged (null) | {embed_unchanged} |",
        f"| **failed total** | **{embed_failed}** |",
        "",
        "### Description Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| ok | {desc_ok} |",
        f"| invalid\\_json | {desc_invalid} |",
        f"| timeout | {desc_timeout} |",
        f"| error | {desc_error} |",
        f"| skipped | {desc_skipped} |",
        "",
    ]

    if embed_failures:
        lines += [
            "### Embedding Failure Table",
            "",
            "| Function | File | Stage | Error Type |",
            "|---|---|---|---|",
        ]
        _CODE_ERROR_MAP = {
            "context_overflow": ("embed", "context_limit"),
            "timeout": ("embed", "timeout"),
            "error": ("embed", "model_error"),
        }
        _DESC_ERROR_MAP = {
            "timeout": ("embed(desc)", "timeout"),
            "invalid_json": ("embed(desc)", "serialization_error"),
            "error": ("embed(desc)", "model_error"),
        }
        for row in embed_failures:
            code_s = row.get("code_status") or ""
            desc_s = row.get("desc_status") or ""
            if code_s in _CODE_ERROR_MAP:
                stage, etype = _CODE_ERROR_MAP[code_s]
                lines.append(f"| `{row['name']}` | {row['file']} | {stage} | {etype} |")
            if desc_s in _DESC_ERROR_MAP:
                stage, etype = _DESC_ERROR_MAP[desc_s]
                lines.append(f"| `{row['name']}` | {row['file']} | {stage} | {etype} |")
        lines.append("")
    else:
        lines += ["_No embedding failures detected._", ""]

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Section 3 — Graph Overview
    # -----------------------------------------------------------------------
    lines += [
        "## Graph Overview",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Production functions indexed | {total} |",
        f"| Test functions ({'included in' if include_tests else 'excluded from'} graph) | {test_funcs} |",
        f"| SIMILAR\\_TO edges | {edges} |",
        f"| Edge density (edges / functions) | {density} |",
        f"| Isolated functions (no edges) | {isolated} |",
        f"| Isolated ratio | {isolated_pct}% |",
        f"| Functions with at least one edge | {total - isolated} |",
        f"| Intra-file edges | {intra} |",
        f"| Inter-file edges | {inter} |",
    ]
    if loc_filtered is not None:
        lines.append(f"| Functions excluded (LOC < {min_loc} threshold) | {loc_filtered} |")
    lines.append("")

    if languages:
        lines += [
            "### Language Breakdown",
            "",
            "| Language | Functions |",
            "|---|---|",
        ]
        for row in languages:
            lines.append(f"| {row['language']} | {row['count']} |")
        lines.append("")

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Section 4 — Similarity Distribution
    # -----------------------------------------------------------------------
    bh = reporter_cfg.sim_dist_bin_high
    bm = reporter_cfg.sim_dist_bin_mid
    bl = reporter_cfg.sim_dist_bin_low
    lines += [
        "## Similarity Distribution",
        "",
        "| Score Range | Edge Count | % of Total |",
        "|---|---|---|",
    ]
    for label, count in [
        (f"> {bh}", gt_high),
        (f"{bm}–{bh}", b_mid_high),
        (f"{bl}–{bm}", b_low_mid),
        (f"≤ {bl}", lt_low),
    ]:
        pct = f"{100 * count / edges:.1f}" if edges > 0 else "0.0"
        lines.append(f"| {label} | {count} | {pct}% |")
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 5 — Top Similar Pairs (unchanged)
    # -----------------------------------------------------------------------
    lines += [
        f"## Top {top_n} Most Similar Pairs",
        "",
        "Potential duplicates or shared logic.",
        "",
        "| Score | Function A | File A | Function B | File B |",
        "|---|---|---|---|---|",
    ]
    for row in top_pairs:
        score = f"{row['score']:.3f}"
        lines.append(
            f"| {score} | `{row['a_name']}` | {row['a_file']} "
            f"| `{row['b_name']}` | {row['b_file']} |"
        )
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 6 — Most Connected Functions (unchanged)
    # -----------------------------------------------------------------------
    lines += [
        f"## Top {top_n} Most Connected Functions",
        "",
        "Functions with the most similarity edges — likely utility or pattern code reused across the codebase.",
        "",
        "| Connections | Function | File |",
        "|---|---|---|",
    ]
    for row in connected:
        lines.append(f"| {row['connections']} | `{row['name']}` | {row['file']} |")
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 7 — Files by Edge Count (enhanced with inter-file ratio)
    # -----------------------------------------------------------------------
    lines += [
        f"## Top {top_n} Files by Edge Count",
        "",
        "Files whose functions are most similar to functions in other files.",
        "",
        "| Edges | Inter-file Ratio | Functions | File |",
        "|---|---|---|---|",
    ]
    for row in per_file:
        ec = row["edge_count"]
        ie = row["inter_edges"] or 0
        ratio = f"{100 * ie / ec:.0f}%" if ec > 0 else "—"
        lines.append(f"| {ec} | {ratio} | {row['fn_count']} | {row['path']} |")
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 8 — Duplication Clusters
    # -----------------------------------------------------------------------
    lines += [
        "## Duplication Clusters",
        "",
        f"Connected components of SIMILAR\\_TO edges with score ≥ {reporter_cfg.cluster_threshold}.",
        "",
    ]
    if clusters:
        lines += [
            "| Cluster ID | Size | Max Score | Avg Score | Files Involved | Representative |",
            "|---|---|---|---|---|---|",
        ]
        for c in clusters:
            files_str = ", ".join(c["files_involved"])
            lines.append(
                f"| {c['id']} | {c['size']} | {c['max_score']:.3f} | {c['avg_score']:.3f}"
                f" | {files_str} | `{c['representative']}` |"
            )
    else:
        lines.append(f"_No clusters found at threshold {reporter_cfg.cluster_threshold}._")
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 9 — Heuristic Flags
    # -----------------------------------------------------------------------
    high_dup    = [c for c in clusters if c["size"] >= reporter_cfg.high_dup_min_cluster_size and c["max_score"] > reporter_cfg.high_dup_min_score]
    cross_file  = [c for c in clusters if len(c["files_involved"]) >= 2]
    coupled_files = [
        row["path"]
        for row in per_file
        if row["edge_count"] >= reporter_cfg.min_coupling_edges
        and (row["inter_edges"] or 0) / row["edge_count"] > reporter_cfg.arch_coupling_threshold
    ]

    flags: list[str] = []
    if high_dup:
        ids = ", ".join(str(c["id"]) for c in high_dup)
        flags.append(
            f"- **HIGH\\_DUPLICATION\\_CLUSTER**: clusters {ids}"
            f" (size ≥ {reporter_cfg.high_dup_min_cluster_size}, max score > {reporter_cfg.high_dup_min_score})"
        )
    if cross_file:
        ids = ", ".join(str(c["id"]) for c in cross_file)
        flags.append(f"- **CROSS\\_FILE\\_DUPLICATION**: clusters {ids} span multiple files")
    if coupled_files:
        file_list = ", ".join(f"`{f}`" for f in coupled_files[:reporter_cfg.max_coupling_files_listed])
        flags.append(f"- **ARCHITECTURE\\_COUPLING**: high inter-file edge ratio in {file_list}")
    if include_tests and cross_edges >= reporter_cfg.test_pollution_threshold:
        flags.append(
            f"- **TEST\\_POLLUTION**: {cross_edges} edges between test and production functions"
        )

    lines += ["## Heuristic Flags", ""]
    lines += flags if flags else ["_No flags raised._"]
    lines += ["", "---", ""]

    export = {
        "repo": repo,
        "timestamp": now,
        "pipeline_version": PIPELINE_VERSION,
        "embedding_model": embed_model,
        "stats": {
            "total_functions": total,
            "test_functions": test_funcs,
            "loc_filtered": loc_filtered,
            "edges": edges,
            "density": density,
            "isolated": isolated,
            "isolated_pct": isolated_pct,
            "intra_edges": intra,
            "inter_edges": inter,
        },
        "embedding": {
            "code": {
                "ok": embed_ok,
                "context_overflow": embed_overflow,
                "timeout": embed_timeout,
                "error": embed_error,
                "skipped": embed_skipped,
                "unchanged": embed_unchanged,
                "failed_total": embed_failed,
            },
            "description": {
                "ok": desc_ok,
                "invalid_json": desc_invalid,
                "timeout": desc_timeout,
                "error": desc_error,
                "skipped": desc_skipped,
            },
        },
        "similarity_distribution": {
            f"gt_{bh}": gt_high,
            f"b_{bm}_{bh}": b_mid_high,
            f"b_{bl}_{bm}": b_low_mid,
            f"lt_{bl}": lt_low,
        },
        "clusters": [
            {
                "id": c["id"],
                "size": c["size"],
                "max_score": round(c["max_score"], 4),
                "avg_score": round(c["avg_score"], 4),
                "files_involved": c["files_involved"],
                "representative": c["representative"],
            }
            for c in clusters
        ],
        "failures": [
            {
                "name": row["name"],
                "file": row["file"],
                "code_status": row.get("code_status"),
                "desc_status": row.get("desc_status"),
            }
            for row in embed_failures
        ],
        "top_pairs": [
            {
                "a_name": row["a_name"],
                "a_file": row["a_file"],
                "b_name": row["b_name"],
                "b_file": row["b_file"],
                "score": round(row["score"], 4),
            }
            for row in top_pairs
        ],
        "flags": {
            "HIGH_DUPLICATION_CLUSTER": [c["id"] for c in high_dup],
            "CROSS_FILE_DUPLICATION": [c["id"] for c in cross_file],
            "ARCHITECTURE_COUPLING": coupled_files,
            "TEST_POLLUTION": cross_edges if include_tests else None,
        },
    }

    return lines, export
