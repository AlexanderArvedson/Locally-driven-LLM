"""Builds the structured JSON export dict for a pipeline report run."""

from __future__ import annotations

from src.pipeline.contracts import ReporterConfig
from src.pipeline.reporting.analysis import _pick_embed_status


def _build_export(
    repo: str,
    now: str,
    pipeline_version: str,
    embed_model: str,
    chat_model: str,
    describer_model: str,
    delta_export: dict | None,
    total: int,
    file_count: int,
    test_funcs: int,
    loc_filtered: int | None,
    edges: int,
    density: float,
    isolated: int,
    isolated_pct: float,
    intra: int,
    inter: int,
    embed_ok: int,
    embed_overflow: int,
    embed_timeout: int,
    embed_error: int,
    embed_skipped: int,
    embed_unchanged: int,
    embed_failed: int,
    desc_ok: int,
    desc_invalid: int,
    desc_timeout: int,
    desc_error: int,
    desc_skipped: int,
    reporter_cfg: ReporterConfig,
    gt_high: int,
    b_mid_high: int,
    b_low_mid: int,
    lt_low: int,
    isolated_fns: list[dict],
    files_by_count: list[dict],
    file_cohesion: list[dict],
    class_cohesion: list[dict],
    clusters: list[dict],
    embed_failures: list[dict],
    top_pairs: list[dict],
    high_dup: list[dict],
    cross_file: list[dict],
    coupled_files: list[str],
    cross_edges: int,
    include_tests: bool,
    low_cohesion_files: list[str],
    god_files: list[str],
    summary_text: str,
) -> dict:
    """Assemble the machine-readable JSON export from pre-computed report data."""
    return {
        "repo": repo,
        "timestamp": now,
        "pipeline_version": pipeline_version,
        "embedding_model": embed_model,
        "chat_model": chat_model,
        "describer_model": describer_model,
        "delta": delta_export,
        "stats": {
            "total_functions": total,
            "file_count": file_count,
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
                "embed_status": _pick_embed_status(row.get("code_status"), row.get("desc_status")),
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
        "summary": summary_text,
    }
