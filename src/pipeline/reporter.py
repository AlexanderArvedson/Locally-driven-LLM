"""Post-run report generator.

Queries Neo4j after a pipeline run and writes a structured markdown report:
embedding integrity, run delta, graph health, similarity distribution, duplication
clusters, heuristic flags, per-file coupling, cohesion scores, and a
machine-readable JSON footer. All logic is deterministic — no LLM usage.
"""

from __future__ import annotations

import json
import math
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

# Updated: intra/inter breakdown replaces simple connection count.
_Q_MOST_CONNECTED: LiteralString = """
MATCH (f:Function {repo: $repo})-[r:SIMILAR_TO]-(b:Function)
WHERE f.isTest = false OR $include_tests
WITH f.qualifiedName AS name, f.filePath AS file,
     count(r) AS connections,
     sum(CASE WHEN b.filePath = f.filePath THEN 1 ELSE 0 END) AS intra,
     sum(CASE WHEN b.filePath <> f.filePath THEN 1 ELSE 0 END) AS inter
ORDER BY connections DESC
LIMIT $limit
RETURN name, file, connections, intra, inter
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

_Q_ISOLATED_FUNCTIONS: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND NOT (f)-[:SIMILAR_TO]-()
RETURN f.qualifiedName AS name, f.filePath AS file,
       f.codeEmbeddingStatus AS code_status,
       f.descriptionStatus AS desc_status
ORDER BY f.filePath, f.qualifiedName
LIMIT $limit
"""

_Q_FILE_EMBEDDINGS: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND (f.codeEmbedding IS NOT NULL OR f.descriptionEmbedding IS NOT NULL)
RETURN f.filePath AS filePath, f.className AS className,
       f.qualifiedName AS qualifiedName,
       f.codeEmbedding AS codeEmbedding,
       f.descriptionEmbedding AS descriptionEmbedding
ORDER BY f.filePath
"""

_Q_FILES_BY_FUNCTION_COUNT: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.filePath AS path, count(f) AS fn_count
ORDER BY fn_count DESC
LIMIT $limit
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
# Cohesion helpers
# ---------------------------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _combined_sim(
    ce_a: list[float] | None,
    de_a: list[float] | None,
    ce_b: list[float] | None,
    de_b: list[float] | None,
    code_w: float,
    desc_w: float,
) -> float | None:
    """Combined similarity matching the weighting used by similarity.py."""
    cs = _cosine(ce_a, ce_b) if ce_a and ce_b else None
    ds = _cosine(de_a, de_b) if de_a and de_b else None
    if cs is not None and ds is not None:
        return code_w * cs + desc_w * ds
    return cs if cs is not None else ds


def _compute_cohesion_scores(
    rows: list[dict],
    group_key: str,
    code_w: float,
    desc_w: float,
    min_functions: int,
) -> list[dict]:
    """Compute average pairwise similarity for each group (file or class).

    Args:
        rows: Query result rows, each with group_key, qualifiedName,
              codeEmbedding, descriptionEmbedding.
        group_key: Field to group by — ``"filePath"`` or ``"className"``.
        code_w: Weight for code embedding similarity.
        desc_w: Weight for description embedding similarity.
        min_functions: Minimum embeddable functions to include a group.

    Returns:
        List of dicts with group, fn_count, cohesion_score, outlier sorted
        ascending by cohesion_score (lowest cohesion first).
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        key = row.get(group_key)
        if key is None:
            continue
        groups[key].append(row)

    results: list[dict] = []
    for group, members in groups.items():
        if len(members) < min_functions:
            continue

        # Track average similarity each member has to the rest (for outlier).
        member_avg: dict[str, list[float]] = {m["qualifiedName"]: [] for m in members}
        all_scores: list[float] = []

        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                score = _combined_sim(
                    a.get("codeEmbedding"),
                    a.get("descriptionEmbedding"),
                    b.get("codeEmbedding"),
                    b.get("descriptionEmbedding"),
                    code_w,
                    desc_w,
                )
                if score is None:
                    continue
                all_scores.append(score)
                member_avg[a["qualifiedName"]].append(score)
                member_avg[b["qualifiedName"]].append(score)

        if not all_scores:
            continue

        cohesion = sum(all_scores) / len(all_scores)

        # Outlier = function with lowest average similarity to its groupmates.
        outlier = min(
            (n for n, scores in member_avg.items() if scores),
            key=lambda n: sum(member_avg[n]) / len(member_avg[n]),
            default=None,
        )

        results.append({
            "group": group,
            "fn_count": len(members),
            "cohesion_score": round(cohesion, 4),
            "outlier": outlier,
        })

    results.sort(key=lambda r: r["cohesion_score"])
    return results


# ---------------------------------------------------------------------------
# Run delta helper
# ---------------------------------------------------------------------------

def _find_previous_report(run_reports_root: Path) -> dict | None:
    """Return the parsed JSON of the most recent prior report, or None."""
    if not run_reports_root.exists():
        return None
    candidates = sorted(run_reports_root.glob("*/report_*.json"), key=lambda p: p.name, reverse=True)
    for candidate in candidates:
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


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

    run_reports_root = Path("run_reports")
    prev_report: dict | None = None

    if output_dir is None:
        output_dir = run_reports_root / ts
        prev_report = _find_previous_report(run_reports_root)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    store = Neo4jStore(neo4j_config)
    try:
        lines, export = await _build_report(
            store, repo_name, include_tests, pipeline_config, loc_filtered, prev_report
        )
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
    prev_report: dict | None = None,
) -> tuple[list[str], dict]:
    db = store._config.database
    driver = store._driver

    reporter_cfg = pipeline_config.reporter if pipeline_config else ReporterConfig()
    top_n = reporter_cfg.top_n
    code_w = pipeline_config.similarity.code_weight if pipeline_config else 0.70
    desc_w = pipeline_config.similarity.description_weight if pipeline_config else 0.30

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
    isolated_fns   = await run(_Q_ISOLATED_FUNCTIONS,      limit=reporter_cfg.max_isolated_listed, include_tests=include_tests)
    file_embed_rows= await run(_Q_FILE_EMBEDDINGS,         include_tests=include_tests)
    files_by_count = await run(_Q_FILES_BY_FUNCTION_COUNT, limit=top_n, include_tests=include_tests)

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

    gt_high    = sim_dist[0]["gt_high"]    if sim_dist else 0
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

    # Cohesion scores (file and class level)
    file_cohesion = _compute_cohesion_scores(
        file_embed_rows, "filePath", code_w, desc_w, reporter_cfg.cohesion_min_functions
    )
    class_cohesion = _compute_cohesion_scores(
        file_embed_rows, "className", code_w, desc_w, reporter_cfg.cohesion_min_functions
    )

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
    # Section 2 — Delta Since Previous Run
    # -----------------------------------------------------------------------
    lines += ["## Delta Since Previous Run", ""]

    delta_export: dict | None = None
    if prev_report:
        prev_ts   = prev_report.get("timestamp", "unknown")
        prev_stats = prev_report.get("stats", {})
        prev_total = prev_stats.get("total_functions", 0)
        prev_edges = prev_stats.get("edges", 0)
        prev_iso   = prev_stats.get("isolated", 0)
        prev_clust = len(prev_report.get("clusters", []))
        curr_clust = len(clusters)

        def _delta(curr: int, prev: int) -> str:
            diff = curr - prev
            return f"+{diff}" if diff > 0 else str(diff)

        lines += [
            f"_Compared against: {prev_ts}_",
            "",
            "| Metric | Previous | Current | Δ |",
            "|---|---|---|---|",
            f"| Functions | {prev_total} | {total} | {_delta(total, prev_total)} |",
            f"| Edges | {prev_edges} | {edges} | {_delta(edges, prev_edges)} |",
            f"| Isolated functions | {prev_iso} | {isolated} | {_delta(isolated, prev_iso)} |",
            f"| Duplication clusters | {prev_clust} | {curr_clust} | {_delta(curr_clust, prev_clust)} |",
            "",
        ]
        delta_export = {
            "previous_timestamp": prev_ts,
            "functions": total - prev_total,
            "edges": edges - prev_edges,
            "isolated": isolated - prev_iso,
            "clusters": curr_clust - prev_clust,
        }
    else:
        lines += ["_No previous run found — delta will appear after the second run._", ""]

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Section 3 — Embedding Integrity
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
    # Section 4 — Graph Overview
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

    # Isolated function list
    lines += [
        "### Isolated Functions",
        "",
        "Functions with no similarity edges — either uniquely specialized, "
        "embedding failed, or dead code candidates.",
        "",
    ]
    if isolated_fns:
        lines += [
            "| Function | File | Embed Status |",
            "|---|---|---|",
        ]
        for row in isolated_fns:
            cs = row.get("code_status") or "ok"
            ds = row.get("desc_status") or "ok"
            status = cs if cs != "ok" else (ds if ds != "ok" else "ok")
            lines.append(f"| `{row['name']}` | {row['file']} | {status} |")
        if isolated > reporter_cfg.max_isolated_listed:
            lines.append(
                f"\n_Showing {reporter_cfg.max_isolated_listed} of {isolated} isolated functions._"
            )
        lines.append("")
    else:
        lines += ["_No isolated functions._", ""]

    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Section 5 — Similarity Distribution
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
    # Section 6 — Top Similar Pairs
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
    # Section 7 — Most Connected Functions (with intra/inter breakdown)
    # -----------------------------------------------------------------------
    lines += [
        f"## Top {top_n} Most Connected Functions",
        "",
        "High intra-file count → local utility. High inter-file count → "
        "cross-codebase pattern or widespread duplication.",
        "",
        "| Connections | Intra-file | Inter-file | Function | File |",
        "|---|---|---|---|---|",
    ]
    for row in connected:
        lines.append(
            f"| {row['connections']} | {row.get('intra', 0)} | {row.get('inter', 0)}"
            f" | `{row['name']}` | {row['file']} |"
        )
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 8 — Files by Edge Count
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
    # Section 9 — Files by Function Count
    # -----------------------------------------------------------------------
    lines += [
        f"## Top {top_n} Files by Function Count",
        "",
        f"Files above {reporter_cfg.god_file_threshold} functions are flagged as GOD\\_FILE.",
        "",
        "| Functions | File |",
        "|---|---|",
    ]
    for row in files_by_count:
        marker = " ⚑" if row["fn_count"] > reporter_cfg.god_file_threshold else ""
        lines.append(f"| {row['fn_count']}{marker} | {row['path']} |")
    lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 10 — File Cohesion Scores
    # -----------------------------------------------------------------------
    lines += [
        "## File Cohesion Scores",
        "",
        "Score = average pairwise embedding similarity of functions within each file. "
        "Low score → semantically unrelated functions → potential SOC violation. "
        "Sorted ascending (most fragmented first).",
        "",
    ]
    display_file_cohesion = file_cohesion[:reporter_cfg.max_cohesion_files_listed]
    if display_file_cohesion:
        lines += [
            "| Cohesion Score | Functions | Outlier | File |",
            "|---|---|---|---|",
        ]
        for c in display_file_cohesion:
            outlier = f"`{c['outlier']}`" if c["outlier"] else "—"
            lines.append(f"| {c['cohesion_score']:.3f} | {c['fn_count']} | {outlier} | {c['group']} |")
        lines.append("")
    else:
        lines += ["_No files with enough embeddable functions to compute cohesion._", ""]
    lines += ["---", ""]

    # -----------------------------------------------------------------------
    # Section 11 — Class Cohesion Scores (omitted if no classes)
    # -----------------------------------------------------------------------
    if class_cohesion:
        lines += [
            "## Class Cohesion Scores",
            "",
            "Score = average pairwise embedding similarity of methods within each class. "
            "Sorted ascending (most fragmented first).",
            "",
            "| Cohesion Score | Methods | Outlier | Class |",
            "|---|---|---|---|",
        ]
        for c in class_cohesion[:reporter_cfg.max_cohesion_files_listed]:
            outlier = f"`{c['outlier']}`" if c["outlier"] else "—"
            lines.append(f"| {c['cohesion_score']:.3f} | {c['fn_count']} | {outlier} | {c['group']} |")
        lines += ["", "---", ""]

    # -----------------------------------------------------------------------
    # Section 12 — Duplication Clusters
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
    # Section 13 — Heuristic Flags
    # -----------------------------------------------------------------------
    high_dup    = [c for c in clusters if c["size"] >= reporter_cfg.high_dup_min_cluster_size and c["max_score"] > reporter_cfg.high_dup_min_score]
    cross_file  = [c for c in clusters if len(c["files_involved"]) >= 2]
    coupled_files = [
        row["path"]
        for row in per_file
        if row["edge_count"] >= reporter_cfg.min_coupling_edges
        and (row["inter_edges"] or 0) / row["edge_count"] > reporter_cfg.arch_coupling_threshold
    ]
    low_cohesion_files = [
        c["group"] for c in file_cohesion
        if c["cohesion_score"] < reporter_cfg.cohesion_low_threshold
        and c["fn_count"] >= reporter_cfg.cohesion_min_functions
    ]
    god_files = [row["path"] for row in files_by_count if row["fn_count"] > reporter_cfg.god_file_threshold]

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
    if low_cohesion_files:
        file_list = ", ".join(f"`{f}`" for f in low_cohesion_files[:reporter_cfg.max_coupling_files_listed])
        flags.append(
            f"- **LOW\\_COHESION**: semantically fragmented files — {file_list}"
            f" (score < {reporter_cfg.cohesion_low_threshold})"
        )
    if god_files:
        file_list = ", ".join(f"`{f}`" for f in god_files[:reporter_cfg.max_coupling_files_listed])
        flags.append(
            f"- **GOD\\_FILE**: files exceeding {reporter_cfg.god_file_threshold} functions — {file_list}"
        )

    lines += ["## Heuristic Flags", ""]
    lines += flags if flags else ["_No flags raised._"]
    lines += ["", "---", ""]

    export = {
        "repo": repo,
        "timestamp": now,
        "pipeline_version": PIPELINE_VERSION,
        "embedding_model": embed_model,
        "delta": delta_export,
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
        "isolated_functions": [
            {
                "name": row["name"],
                "file": row["file"],
                "embed_status": (row.get("code_status") or "ok")
                    if (row.get("code_status") or "ok") != "ok"
                    else (row.get("desc_status") or "ok"),
            }
            for row in isolated_fns
        ],
        "files_by_function_count": [
            {"path": row["path"], "fn_count": row["fn_count"]}
            for row in files_by_count
        ],
        "file_cohesion": [
            {
                "file": c["group"],
                "fn_count": c["fn_count"],
                "cohesion_score": c["cohesion_score"],
                "outlier": c["outlier"],
            }
            for c in file_cohesion
        ],
        "class_cohesion": [
            {
                "class": c["group"],
                "fn_count": c["fn_count"],
                "cohesion_score": c["cohesion_score"],
                "outlier": c["outlier"],
            }
            for c in class_cohesion
        ],
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
            "LOW_COHESION": low_cohesion_files,
            "GOD_FILE": god_files,
        },
    }

    return lines, export
