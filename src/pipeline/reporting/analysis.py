"""Pure Python analysis functions for the pipeline report.

These helpers operate on data already retrieved from Neo4j and have no
database dependencies — they can be tested without a running graph instance.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from pathlib import Path


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


def _pick_embed_status(code_status: str | None, desc_status: str | None) -> str:
    """Return the most informative non-ok embed status for a function row.

    Prefers code_embedding_status; falls back to description_status, treating
    'skipped' and 'ok' as unremarkable so they don't surface in reports.
    """
    cs = code_status or "ok"
    if cs != "ok":
        return cs
    ds = desc_status or "ok"
    return ds if ds not in ("ok", "skipped") else "ok"


def _find_previous_report(run_reports_root: Path) -> dict | None:
    """Return the parsed JSON of the most recent prior report, or None."""
    if not run_reports_root.exists():
        return None
    candidates = sorted(run_reports_root.glob("*/*_report_*.json"), key=lambda p: p.name, reverse=True)
    for candidate in candidates:
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None
