"""Markdown section renderers for the pipeline report.

Re-exports all render_* functions from sub-modules so callers can import from
``src.pipeline.reporting.markdown`` without knowing the internal layout.
"""

from src.pipeline.reporting.markdown.integrity import render_embedding_integrity
from src.pipeline.reporting.markdown.overview import render_delta, render_metadata, render_summary
from src.pipeline.reporting.markdown.quality import (
    render_class_cohesion,
    render_duplication_clusters,
    render_file_cohesion,
    render_heuristic_flags,
)
from src.pipeline.reporting.markdown.topology import (
    render_files_by_edge_count,
    render_files_by_function_count,
    render_graph_overview,
    render_most_connected,
    render_similarity_distribution,
    render_top_pairs,
)

__all__ = [
    "render_metadata",
    "render_summary",
    "render_delta",
    "render_embedding_integrity",
    "render_graph_overview",
    "render_similarity_distribution",
    "render_top_pairs",
    "render_most_connected",
    "render_files_by_edge_count",
    "render_files_by_function_count",
    "render_file_cohesion",
    "render_class_cohesion",
    "render_duplication_clusters",
    "render_heuristic_flags",
]
