"""Markdown section renderers for the pipeline report.

Each function accepts pre-computed data and returns a list of markdown lines.
No database I/O, no LLM calls — pure formatting logic.
"""

from __future__ import annotations

from src.pipeline.contracts import ReporterConfig
from src.pipeline.reporting.analysis import _pick_embed_status


def render_metadata(
    repo: str,
    db: str,
    now: str,
    pipeline_version: str,
    embed_model: str,
    chat_model: str,
    describer_model: str,
    min_loc: int,
    timezone: str,
) -> list[str]:
    """Section 1 — report header and metadata table."""
    lines: list[str] = [
        f"# Pipeline Report — `{repo}`",
        "",
        "## Metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Repository | `{repo}` |",
        f"| Generated ({timezone}) | {now} |",
        f"| Neo4j database | `{db}` |",
        f"| Pipeline version | {pipeline_version} |",
        f"| Embedding model | `{embed_model}` |",
        f"| Chat model | `{chat_model}` |",
        f"| Describer model | `{describer_model}` |",
    ]
    if min_loc > 0:
        lines.append(f"| Min LOC threshold | {min_loc} |")
    lines += ["", "---", ""]
    return lines


def render_summary(
    total: int,
    embed_failed: int,
    clusters: list[dict],
    high_dup: list[dict],
    coupled_files: list[str],
    low_cohesion_files: list[str],
    god_files: list[str],
    isolated: int,
    languages: list[dict],
    files_by_count: list[dict],
) -> tuple[list[str], str]:
    """Section 1b — one-paragraph executive summary placed after the metadata table.

    Returns ``(markdown_lines, summary_text)`` so callers can use the plain-text
    paragraph directly (e.g. for JSON export) without indexing into the list.
    """
    lang_names = [row["language"] for row in languages if row.get("language")]
    if not lang_names:
        lang_summary = "unknown"
    elif len(lang_names) == 1:
        lang_summary = lang_names[0]
    elif len(lang_names) == 2:
        lang_summary = f"{lang_names[0]} and {lang_names[1]}"
    else:
        lang_summary = ", ".join(lang_names[:-1]) + f", and {lang_names[-1]}"

    flag_count = sum([bool(high_dup), bool(god_files), bool(coupled_files), bool(low_cohesion_files), isolated > 0])

    # Cluster with the broadest spread across files — most worth consolidating
    primary_target = max(clusters, key=lambda c: c["size"] * len(c["files_involved"]), default=None)

    sentences: list[str] = [
        f"{total} functions indexed across {lang_summary}. {flag_count} concern(s) detected."
    ]

    if high_dup:
        c = primary_target if primary_target is not None else high_dup[0]
        sentences.append(
            f"Duplication is the dominant concern: cluster {c['id']} groups {c['size']} functions "
            f"across {len(c['files_involved'])} file(s) — primary consolidation target is `{c['representative']}`."
        )
        lead = "high_dup"
    elif god_files:
        fn_count = next((r["fn_count"] for r in files_by_count if r["path"] == god_files[0]), "?")
        sentences.append(
            f"{len(god_files)} god file(s) flagged ({god_files[0]} is largest at {fn_count} functions)."
        )
        lead = "god_files"
    elif coupled_files:
        sentences.append(
            f"{len(coupled_files)} file(s) exhibit high inter-file coupling — architectural boundaries may need review."
        )
        lead = "coupled"
    elif low_cohesion_files:
        sentences.append(
            f"{len(low_cohesion_files)} file(s) show low semantic cohesion, suggesting mixed responsibilities."
        )
        lead = "low_cohesion"
    elif isolated > 0:
        sentences.append(
            f"{isolated} function(s) are isolated (no similarity edges) — potential dead code candidates."
        )
        lead = "isolated"
    else:
        sentences.append("No high-severity concerns detected.")
        lead = "clean"

    if god_files and lead != "god_files":
        fn_count = next((r["fn_count"] for r in files_by_count if r["path"] == god_files[0]), "?")
        sentences.append(
            f"{len(god_files)} god file(s) flagged ({god_files[0]} is largest at {fn_count} functions)."
        )

    if (low_cohesion_files or coupled_files) and lead not in ("low_cohesion", "coupled"):
        parts: list[str] = []
        if low_cohesion_files:
            parts.append(
                f"{len(low_cohesion_files)} file(s) show low semantic cohesion, suggesting mixed responsibilities."
            )
        if coupled_files:
            parts.append(f"{len(coupled_files)} file(s) exhibit high inter-file coupling.")
        sentences.append(" ".join(parts))

    if embed_failed > 0:
        sentences.append(
            f"{embed_failed} function(s) could not be embedded and are excluded from similarity analysis."
        )

    text = " ".join(sentences)
    return ["## Executive Summary", "", text, "", "---", ""], text


def render_delta(
    prev_report: dict | None,
    total: int,
    edges: int,
    isolated: int,
    n_clusters: int,
    file_count: int = 0,
) -> tuple[list[str], dict | None]:
    """Section 2 — delta since previous run.

    Returns the markdown lines and the delta dict for the JSON export (or None
    if there is no previous report to compare against).
    """
    lines: list[str] = ["## Delta Since Previous Run", ""]
    delta_export: dict | None = None

    if prev_report:
        prev_ts         = prev_report.get("timestamp", "unknown")
        prev_stats      = prev_report.get("stats", {})
        prev_total      = prev_stats.get("total_functions", 0)
        prev_files      = prev_stats.get("file_count", 0)
        prev_edges      = prev_stats.get("edges", 0)
        prev_iso        = prev_stats.get("isolated", 0)
        prev_clust      = len(prev_report.get("clusters", []))

        def _delta(curr: int, prev: int) -> str:
            diff = curr - prev
            return f"+{diff}" if diff > 0 else str(diff)

        lines += [
            f"_Compared against: {prev_ts}_",
            "",
            "| Metric | Previous | Current | Δ |",
            "|---|---|---|---|",
            f"| Files | {prev_files} | {file_count} | {_delta(file_count, prev_files)} |",
            f"| Functions | {prev_total} | {total} | {_delta(total, prev_total)} |",
            f"| Edges | {prev_edges} | {edges} | {_delta(edges, prev_edges)} |",
            f"| Isolated functions | {prev_iso} | {isolated} | {_delta(isolated, prev_iso)} |",
            f"| Duplication clusters | {prev_clust} | {n_clusters} | {_delta(n_clusters, prev_clust)} |",
            "",
        ]
        delta_export = {
            "previous_timestamp": prev_ts,
            "files": file_count - prev_files,
            "functions": total - prev_total,
            "edges": edges - prev_edges,
            "isolated": isolated - prev_iso,
            "clusters": n_clusters - prev_clust,
        }
    else:
        lines += ["_No previous run found — delta will appear after the second run._", ""]

    lines += ["---", ""]
    return lines, delta_export


def render_embedding_integrity(
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
    embed_failures: list[dict],
) -> list[str]:
    """Section 3 — embedding and description coverage tables."""
    lines: list[str] = [
        "## Embedding Integrity",
        "",
        "### Code Embedding Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| ok | {embed_ok} |",
        f"| context_overflow | {embed_overflow} |",
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
        f"| invalid_json | {desc_invalid} |",
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
    return lines


def render_graph_overview(
    total: int,
    test_funcs: int,
    edges: int,
    density: float,
    isolated: int,
    isolated_pct: float,
    intra: int,
    inter: int,
    include_tests: bool,
    loc_filtered: int | None,
    min_loc: int,
    languages: list[dict],
    isolated_fns: list[dict],
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 4 — graph overview statistics, language breakdown, and isolated functions."""
    lines: list[str] = [
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
            status = _pick_embed_status(row.get("code_status"), row.get("desc_status"))
            lines.append(f"| `{row['name']}` | {row['file']} | {status} |")
        if isolated > reporter_cfg.max_isolated_listed:
            lines.append(
                f"\n_Showing {reporter_cfg.max_isolated_listed} of {isolated} isolated functions._"
            )
        lines.append("")
    else:
        lines += ["_No isolated functions._", ""]

    lines += ["---", ""]
    return lines


def render_similarity_distribution(
    gt_high: int,
    b_mid_high: int,
    b_low_mid: int,
    lt_low: int,
    edges: int,
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 5 — similarity score distribution across four bins."""
    bh = reporter_cfg.sim_dist_bin_high
    bm = reporter_cfg.sim_dist_bin_mid
    bl = reporter_cfg.sim_dist_bin_low
    lines: list[str] = [
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
    return lines


def render_top_pairs(top_pairs: list[dict], top_n: int) -> list[str]:
    """Section 6 — top N most similar function pairs."""
    lines: list[str] = [
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
    return lines


def render_most_connected(connected: list[dict], top_n: int) -> list[str]:
    """Section 7 — top N most connected functions with intra/inter breakdown."""
    lines: list[str] = [
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
    return lines


def render_files_by_edge_count(per_file: list[dict], top_n: int) -> list[str]:
    """Section 8 — top N files by total edge count."""
    lines: list[str] = [
        f"## Top {top_n} Files by Edge Count",
        "",
        "Files ranked by total SIMILAR_TO edge count; inter-file ratio indicates cross-boundary coupling.",
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
    return lines


def render_files_by_function_count(
    files_by_count: list[dict],
    top_n: int,
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 9 — top N files by function count, flagging god files."""
    lines: list[str] = [
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
    return lines


def render_file_cohesion(
    file_cohesion: list[dict],
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 10 — file cohesion scores (ascending, most fragmented first)."""
    lines: list[str] = [
        "## File Cohesion Scores",
        "",
        "Score = average pairwise embedding similarity of functions within each file. "
        "Low score → semantically unrelated functions → potential SOC violation. "
        "Sorted ascending (most fragmented first).",
        "",
    ]
    display = file_cohesion[:reporter_cfg.max_cohesion_files_listed]
    if display:
        lines += [
            "| Cohesion Score | Functions | Outlier | File |",
            "|---|---|---|---|",
        ]
        for c in display:
            outlier = f"`{c['outlier']}`" if c["outlier"] else "—"
            lines.append(f"| {c['cohesion_score']:.3f} | {c['fn_count']} | {outlier} | {c['group']} |")
        lines.append("")
    else:
        lines += ["_No files with enough embeddable functions to compute cohesion._", ""]
    lines += ["---", ""]
    return lines


def render_class_cohesion(
    class_cohesion: list[dict],
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 11 — class cohesion scores (omitted when no classes present)."""
    if not class_cohesion:
        return []
    lines: list[str] = [
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
    return lines


def render_duplication_clusters(
    clusters: list[dict],
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 12 — duplication clusters at the configured similarity threshold."""
    lines: list[str] = [
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
    return lines


def render_heuristic_flags(
    high_dup: list[dict],
    cross_file: list[dict],
    coupled_files: list[str],
    low_cohesion_files: list[str],
    god_files: list[str],
    cross_edges: int,
    include_tests: bool,
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 13 — heuristic flags raised by the analysis."""
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

    lines: list[str] = ["## Heuristic Flags", ""]
    lines += flags if flags else ["_No flags raised._"]
    lines += ["", "---", ""]
    return lines
