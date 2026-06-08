"""Post-run report generator.

Queries Neo4j after a pipeline run and writes a structured markdown report:
embedding integrity, run delta, graph health, similarity distribution, duplication
clusters, heuristic flags, per-file coupling, cohesion scores, and a
machine-readable JSON footer. All logic is deterministic — no LLM usage.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Final, LiteralString
from zoneinfo import ZoneInfo

from src.pipeline.contracts import Neo4jConfig, PipelineConfig, ReporterConfig
from src.pipeline.graph.store import Neo4jStore
from src.pipeline.reporting.analysis import (
    _compute_clusters,
    _compute_cohesion_scores,
    _find_previous_report,
)
from src.pipeline.reporting.markdown import (
    render_class_cohesion,
    render_delta,
    render_duplication_clusters,
    render_embedding_integrity,
    render_file_cohesion,
    render_files_by_edge_count,
    render_files_by_function_count,
    render_graph_overview,
    render_heuristic_flags,
    render_metadata,
    render_most_connected,
    render_similarity_distribution,
    render_summary,
    render_top_pairs,
)
from src.pipeline.reporting.queries import (
    _Q_CLUSTER_EDGES,
    _Q_DESCRIPTION_COVERAGE,
    _Q_EMBEDDING_COVERAGE,
    _Q_EMBEDDING_FAILURES,
    _Q_FILE_EMBEDDINGS,
    _Q_FILES_BY_FUNCTION_COUNT,
    _Q_INTRA_INTER_EDGES,
    _Q_ISOLATED_FUNCTIONS,
    _Q_LANGUAGE_BREAKDOWN,
    _Q_MOST_CONNECTED,
    _Q_NO_EDGES,
    _Q_PER_FILE_INTER,
    _Q_SIMILARITY_DISTRIBUTION,
    _Q_STATS,
    _Q_TEST_COUNT,
    _Q_TEST_POLLUTION,
    _Q_TOP_PAIRS,
)

PIPELINE_VERSION: Final[str] = "2.0"


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

    store = Neo4jStore(neo4j_config)
    try:
        lines, export = await _build_report(
            store, repo_name, include_tests, pipeline_config, loc_filtered, prev_report
        )
    finally:
        await store.close()

    # Only create the directory once we have content to write.
    output_dir.mkdir(parents=True, exist_ok=True)
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
    files_by_count = await run(_Q_FILES_BY_FUNCTION_COUNT, limit=top_n, include_tests=include_tests)

    # Fetch raw embeddings for cohesion computation. This query returns all
    # embedding vectors and can be large — fall back to empty on failure so a
    # Neo4j timeout or memory pressure here does not abort the whole report.
    try:
        file_embed_rows = await run(_Q_FILE_EMBEDDINGS, include_tests=include_tests)
    except Exception as exc:
        from loguru import logger
        logger.warning("[reporter] cohesion query failed ({}), skipping cohesion sections", exc)
        file_embed_rows = []

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

    # Heuristic flag lists — computed here so both render_summary and render_heuristic_flags share them
    high_dup = [c for c in clusters if c["size"] >= reporter_cfg.high_dup_min_cluster_size and c["max_score"] > reporter_cfg.high_dup_min_score]
    cross_file = [c for c in clusters if len(c["files_involved"]) >= 2]
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

    tz = ZoneInfo(reporter_cfg.timezone)
    now_dt = datetime.now(tz)
    tz_abbr = now_dt.strftime("%Z") or reporter_cfg.timezone
    now = now_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")
    embed_model = pipeline_config.embedding_model if pipeline_config else "N/A"
    min_loc = pipeline_config.limits.min_loc_threshold if pipeline_config else 0

    lines: list[str] = []

    lines += render_metadata(repo, db, now, PIPELINE_VERSION, embed_model, min_loc, reporter_cfg.timezone)

    summary_lines = render_summary(
        total, embed_failed, clusters, high_dup,
        coupled_files, low_cohesion_files, god_files,
        isolated, languages, files_by_count,
    )
    lines += summary_lines

    delta_lines, delta_export = render_delta(prev_report, total, edges, isolated, len(clusters))
    lines += delta_lines

    lines += render_embedding_integrity(
        embed_ok, embed_overflow, embed_timeout, embed_error, embed_skipped, embed_unchanged,
        embed_failed, desc_ok, desc_invalid, desc_timeout, desc_error, desc_skipped,
        embed_failures,
    )

    lines += render_graph_overview(
        total, test_funcs, edges, density, isolated, isolated_pct, intra, inter,
        include_tests, loc_filtered, min_loc, languages, isolated_fns, reporter_cfg,
    )

    lines += render_similarity_distribution(gt_high, b_mid_high, b_low_mid, lt_low, edges, reporter_cfg)
    lines += render_top_pairs(top_pairs, top_n)
    lines += render_most_connected(connected, top_n)
    lines += render_files_by_edge_count(per_file, top_n)
    lines += render_files_by_function_count(files_by_count, top_n, reporter_cfg)
    lines += render_file_cohesion(file_cohesion, reporter_cfg)
    lines += render_class_cohesion(class_cohesion, reporter_cfg)
    lines += render_duplication_clusters(clusters, reporter_cfg)

    lines += render_heuristic_flags(
        high_dup, cross_file, coupled_files, low_cohesion_files, god_files,
        cross_edges, include_tests, reporter_cfg,
    )

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
            f"gt_{reporter_cfg.sim_dist_bin_high}": gt_high,
            f"b_{reporter_cfg.sim_dist_bin_mid}_{reporter_cfg.sim_dist_bin_high}": b_mid_high,
            f"b_{reporter_cfg.sim_dist_bin_low}_{reporter_cfg.sim_dist_bin_mid}": b_low_mid,
            f"lt_{reporter_cfg.sim_dist_bin_low}": lt_low,
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
        "summary": summary_lines[2],
    }

    return lines, export
