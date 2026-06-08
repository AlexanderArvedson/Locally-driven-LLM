"""Markdown renderers for the report header and run-level overview sections.

Covers: Metadata, Executive Summary, Delta Since Previous Run.
"""

from __future__ import annotations


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
