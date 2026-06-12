"""Post-run report generator.

Queries Neo4j after a pipeline run and writes a structured markdown report:
embedding integrity, run delta, graph health, similarity distribution, duplication
clusters, heuristic flags, per-file coupling, cohesion scores, and a
machine-readable JSON footer. All logic is deterministic — no LLM usage.
"""

from __future__ import annotations

import asyncio
import json
import time
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
    _compute_flags,
    _find_previous_report,
)
from src.pipeline.reporting.export import _build_export
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
    _Q_CHUNKED_FUNCTIONS,
    _Q_CLUSTER_EDGES,
    _Q_DESCRIPTION_COVERAGE,
    _Q_EMBEDDING_COVERAGE,
    _Q_EMBEDDING_FAILURES,
    _Q_FILE_COUNT,
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
) -> tuple[Path, str]:
    """Query Neo4j and write a report directory containing report.md and report.json.

    Args:
        neo4j_config: Connection settings for Neo4j.
        repo_name: The repository name to report on.
        output_dir: Directory to write the two report files into. Defaults to
            ``run_reports/<repo_name>/<timestamp>/`` relative to the current working
            directory. Created automatically if it does not exist.
        include_tests: Whether to include test functions in graph stats.
        pipeline_config: Full pipeline config for metadata and reporter
            thresholds. When None, defaults from ReporterConfig are used
            and model name is shown as "N/A".

    Returns:
        Tuple of (path to the generated report.md file, full markdown text).
    """
    reporter_cfg = pipeline_config.reporter if pipeline_config else ReporterConfig()
    ts = datetime.now(ZoneInfo(reporter_cfg.timezone)).strftime("%Y%m%d-%H%M%S")
    sanitized_repo = repo_name.replace("/", "_").replace("\\", "_").replace(" ", "_").replace(":", "_")

    run_reports_root = Path("run_reports")
    repo_dir = run_reports_root / sanitized_repo
    prev_report: dict | None = _find_previous_report(repo_dir)

    if output_dir is None:
        output_dir = repo_dir / ts

    output_dir = Path(output_dir)

    store = Neo4jStore(neo4j_config)
    t0 = time.monotonic()
    try:
        lines, export = await _build_report(
            store, repo_name, include_tests, pipeline_config, loc_filtered, prev_report
        )
    finally:
        await store.close()
    duration_s = round(time.monotonic() - t0, 1)
    export["duration_s"] = duration_s
    # Inject duration row into the metadata table (ends at the first "---" in lines).
    try:
        sep_idx = lines.index("---")
        lines.insert(sep_idx - 1, f"| Report generated in | {duration_s:.1f}s |")
    except ValueError:
        pass

    md_text = "\n".join(lines)

    # Only create the directory once we have content to write.
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{sanitized_repo}_report_{ts}.md"
    md_path.write_text(md_text, encoding="utf-8")
    (output_dir / f"{sanitized_repo}_report_{ts}.json").write_text(json.dumps(export, indent=2), encoding="utf-8")
    return md_path, md_text


async def _build_report(
    store: Neo4jStore,
    repo: str,
    include_tests: bool,
    pipeline_config: PipelineConfig | None,
    loc_filtered: int | None = None,
    prev_report: dict | None = None,
) -> tuple[list[str], dict]:
    db = store.database_name

    reporter_cfg = pipeline_config.reporter if pipeline_config else ReporterConfig()
    top_n = reporter_cfg.top_n
    code_w = pipeline_config.similarity.code_weight if pipeline_config else 0.70
    desc_w = pipeline_config.similarity.description_weight if pipeline_config else 0.30

    async def run(query: LiteralString, **params) -> list[dict]:
        return await store.run_query(query, repo=repo, **params)

    # Run all independent queries concurrently.
    (
        stats,
        test_count,
        no_edges,
        top_pairs,
        connected,
        languages,
        embed_cov,
        desc_cov,
        embed_failures,
        chunked_functions,
        intra_inter,
        sim_dist,
        per_file,
        cluster_edges,
        isolated_fns,
        files_by_count,
        file_count_rows,
    ) = await asyncio.gather(
        run(_Q_STATS,                   include_tests=include_tests),
        run(_Q_TEST_COUNT),
        run(_Q_NO_EDGES,                include_tests=include_tests),
        run(_Q_TOP_PAIRS,               limit=top_n, include_tests=include_tests),
        run(_Q_MOST_CONNECTED,          limit=top_n, include_tests=include_tests),
        run(_Q_LANGUAGE_BREAKDOWN,      include_tests=include_tests),
        run(_Q_EMBEDDING_COVERAGE,      include_tests=include_tests),
        run(_Q_DESCRIPTION_COVERAGE,    include_tests=include_tests),
        run(_Q_EMBEDDING_FAILURES,      limit=reporter_cfg.max_embedding_failures, include_tests=include_tests),
        run(_Q_CHUNKED_FUNCTIONS,       limit=reporter_cfg.max_embedding_failures, include_tests=include_tests),
        run(_Q_INTRA_INTER_EDGES,       include_tests=include_tests),
        run(_Q_SIMILARITY_DISTRIBUTION,
            bin_high=reporter_cfg.sim_dist_bin_high,
            bin_mid=reporter_cfg.sim_dist_bin_mid,
            bin_low=reporter_cfg.sim_dist_bin_low,
            include_tests=include_tests),
        run(_Q_PER_FILE_INTER,          limit=top_n, include_tests=include_tests),
        run(_Q_CLUSTER_EDGES,           threshold=reporter_cfg.cluster_threshold, include_tests=include_tests),
        run(_Q_ISOLATED_FUNCTIONS,      limit=reporter_cfg.max_isolated_listed, include_tests=include_tests),
        run(_Q_FILES_BY_FUNCTION_COUNT, limit=top_n, include_tests=include_tests),
        run(_Q_FILE_COUNT,              include_tests=include_tests),
    )

    test_pollution = await run(_Q_TEST_POLLUTION) if include_tests else [{"cross_edges": 0}]

    # Fetch raw embeddings for cohesion computation. Bounded by cohesion_max_functions
    # to cap the O(n²) pairwise computation and avoid large result sets.
    # Falls back to empty on failure so a timeout here does not abort the whole report.
    try:
        file_embed_rows = await run(
            _Q_FILE_EMBEDDINGS,
            include_tests=include_tests,
            limit=reporter_cfg.cohesion_max_functions,
        )
    except Exception as exc:
        from loguru import logger
        logger.warning("[reporter] cohesion query failed ({}), skipping cohesion sections", exc)
        file_embed_rows = []

    # Scalar extraction
    total       = stats[0]["total"]      if stats           else 0
    edges       = stats[0]["edges"]      if stats           else 0
    file_count  = file_count_rows[0]["file_count"] if file_count_rows else 0
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
    embed_chunked  = embed_by_status.get("chunked", 0)
    embed_timeout  = embed_by_status.get("timeout", 0)
    embed_error    = embed_by_status.get("error", 0)
    embed_skipped  = embed_by_status.get("skipped", 0)
    embed_unchanged = embed_by_status.get("null", 0)
    embed_failed   = embed_timeout + embed_error

    desc_ok      = desc_by_status.get("ok", 0)
    desc_invalid = desc_by_status.get("invalid_json", 0)
    desc_timeout = desc_by_status.get("timeout", 0)
    desc_error   = desc_by_status.get("error", 0)
    desc_skipped = desc_by_status.get("skipped", 0)

    clusters = _compute_clusters(cluster_edges)

    file_cohesion = _compute_cohesion_scores(
        file_embed_rows, "filePath", code_w, desc_w, reporter_cfg.cohesion_min_functions
    )
    class_cohesion = _compute_cohesion_scores(
        file_embed_rows, "className", code_w, desc_w, reporter_cfg.cohesion_min_functions
    )

    high_dup, cross_file, coupled_files, low_cohesion_files, god_files = _compute_flags(
        clusters, per_file, file_cohesion, files_by_count, reporter_cfg
    )

    tz = ZoneInfo(reporter_cfg.timezone)
    now_dt = datetime.now(tz)
    tz_abbr = now_dt.strftime("%Z") or reporter_cfg.timezone
    now = now_dt.strftime(f"%Y-%m-%d %H:%M {tz_abbr}")
    embed_model     = pipeline_config.embedding_model  if pipeline_config else "N/A"
    chat_model      = pipeline_config.chat_model       if pipeline_config else "N/A"
    describer_model = pipeline_config.describer_model  if pipeline_config else "N/A"
    min_loc         = pipeline_config.limits.min_loc_threshold if pipeline_config else 0

    lines: list[str] = []

    lines += render_metadata(
        repo, db, now, PIPELINE_VERSION,
        embed_model, chat_model, describer_model,
        min_loc, reporter_cfg.timezone,
    )

    summary_lines, summary_text = render_summary(
        total, embed_failed, clusters, high_dup,
        coupled_files, low_cohesion_files, god_files,
        isolated, languages, files_by_count,
    )
    lines += summary_lines

    delta_lines, delta_export = render_delta(prev_report, total, edges, isolated, len(clusters), file_count)
    lines += delta_lines

    lines += render_embedding_integrity(
        embed_ok, embed_chunked, embed_timeout, embed_error, embed_skipped, embed_unchanged,
        embed_failed, desc_ok, desc_invalid, desc_timeout, desc_error, desc_skipped,
        embed_failures, chunked_functions,
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

    export = _build_export(
        repo=repo,
        now=now,
        pipeline_version=PIPELINE_VERSION,
        embed_model=embed_model,
        chat_model=chat_model,
        describer_model=describer_model,
        delta_export=delta_export,
        total=total,
        file_count=file_count,
        test_funcs=test_funcs,
        loc_filtered=loc_filtered,
        edges=edges,
        density=density,
        isolated=isolated,
        isolated_pct=isolated_pct,
        intra=intra,
        inter=inter,
        embed_ok=embed_ok,
        embed_chunked=embed_chunked,
        embed_timeout=embed_timeout,
        embed_error=embed_error,
        embed_skipped=embed_skipped,
        embed_unchanged=embed_unchanged,
        embed_failed=embed_failed,
        desc_ok=desc_ok,
        desc_invalid=desc_invalid,
        desc_timeout=desc_timeout,
        desc_error=desc_error,
        desc_skipped=desc_skipped,
        reporter_cfg=reporter_cfg,
        gt_high=gt_high,
        b_mid_high=b_mid_high,
        b_low_mid=b_low_mid,
        lt_low=lt_low,
        isolated_fns=isolated_fns,
        files_by_count=files_by_count,
        file_cohesion=file_cohesion,
        class_cohesion=class_cohesion,
        clusters=clusters,
        embed_failures=embed_failures,
        chunked_functions=chunked_functions,
        top_pairs=top_pairs,
        high_dup=high_dup,
        cross_file=cross_file,
        coupled_files=coupled_files,
        cross_edges=cross_edges,
        include_tests=include_tests,
        low_cohesion_files=low_cohesion_files,
        god_files=god_files,
        summary_text=summary_text,
    )

    return lines, export
