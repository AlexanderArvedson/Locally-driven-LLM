"""Markdown renderers for graph topology and similarity sections.

Covers: Graph Overview, Similarity Distribution, Top Pairs, Most Connected,
Files by Edge Count, Files by Function Count.
"""

from __future__ import annotations

from src.pipeline.contracts import ReporterConfig
from src.pipeline.reporting.analysis import _pick_embed_status


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
        f"| Similarity edges | {edges} |",
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
    _band_labels = ["near-identical", "highly similar", "similar", "low similarity"]
    for (label, count), desc in zip(
        [
            (f"> {bh}", gt_high),
            (f"{bm}–{bh}", b_mid_high),
            (f"{bl}–{bm}", b_low_mid),
            (f"≤ {bl}", lt_low),
        ],
        _band_labels,
    ):
        pct = f"{100 * count / edges:.1f}" if edges > 0 else "0.0"
        lines.append(f"| {label} ({desc}) | {count} | {pct}% |")
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
        f"Files above {reporter_cfg.god_file_threshold} functions are flagged as god files.",
        "",
        "| Functions | File |",
        "|---|---|",
    ]
    for row in files_by_count:
        marker = " ⚑" if row["fn_count"] > reporter_cfg.god_file_threshold else ""
        lines.append(f"| {row['fn_count']}{marker} | {row['path']} |")
    lines += ["", "---", ""]
    return lines
