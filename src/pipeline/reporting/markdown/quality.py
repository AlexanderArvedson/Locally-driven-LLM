"""Markdown renderers for code-quality analysis sections.

Covers: File Cohesion, Class Cohesion, Duplication Clusters, Heuristic Flags.
"""

from __future__ import annotations

from src.pipeline.contracts import ReporterConfig


def render_file_cohesion(
    file_cohesion: list[dict],
    reporter_cfg: ReporterConfig,
) -> list[str]:
    """Section 10 — file cohesion scores (ascending, most fragmented first)."""
    lines: list[str] = [
        "## File Cohesion Scores",
        "",
        "Score = average pairwise embedding similarity of functions within each file. "
        "Low score → semantically unrelated functions → potential separation of concerns violation. "
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
        f"Connected components of similarity edges with score ≥ {reporter_cfg.cluster_threshold}.",
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
        cluster_word = "clusters" if len(high_dup) > 1 else "cluster"
        flags.append(
            f"- **High duplication** ({cluster_word} {ids}): large groups of near-identical functions"
            f" (size ≥ {reporter_cfg.high_dup_min_cluster_size}, max score > {reporter_cfg.high_dup_min_score})"
        )
    if cross_file:
        ids = ", ".join(str(c["id"]) for c in cross_file)
        cluster_word = "clusters" if len(cross_file) > 1 else "cluster"
        flags.append(f"- **Cross-file duplication** ({cluster_word} {ids}): same logic copied across multiple files")
    if coupled_files:
        file_list = ", ".join(f"`{f}`" for f in coupled_files[:reporter_cfg.max_coupling_files_listed])
        flags.append(f"- **High coupling**: some files heavily depended on across the codebase — {file_list}")
    if include_tests and cross_edges >= reporter_cfg.test_pollution_threshold:
        flags.append(
            f"- **Test pollution**: {cross_edges} edges between test and production functions"
        )
    if low_cohesion_files:
        file_list = ", ".join(f"`{f}`" for f in low_cohesion_files[:reporter_cfg.max_coupling_files_listed])
        flags.append(
            f"- **Low cohesion**: semantically fragmented files — {file_list}"
            f" (score < {reporter_cfg.cohesion_low_threshold})"
        )
    if god_files:
        file_list = ", ".join(f"`{f}`" for f in god_files[:reporter_cfg.max_coupling_files_listed])
        flags.append(
            f"- **God files**: files with >{reporter_cfg.god_file_threshold} functions — {file_list}"
        )

    lines: list[str] = ["## Heuristic Flags", ""]
    lines += flags if flags else ["_No flags raised._"]
    lines += ["", "---", ""]
    return lines
