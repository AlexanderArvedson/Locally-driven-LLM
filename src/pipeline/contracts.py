"""Data contracts for the function embedding pipeline.

All dataclasses here are plain mutable (not frozen) so the pipeline can
progressively enrich FunctionRecord instances as each stage completes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FunctionRecord:
    """One extracted function or method from a source file."""

    id: str
    repo: str
    language: str
    file_path: str
    function_name: str
    qualified_name: str          # "ClassName.method_name" or "function_name"
    class_name: str | None
    start_line: int
    end_line: int
    source_code: str
    source_hash: str             # sha256(source_code), hex digest
    description: str | None = None           # JSON string from LLM
    code_embedding: list[float] | None = None
    description_embedding: list[float] | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_seen_at: str = field(default_factory=_now_iso)
    is_deleted: bool = False
    is_test: bool = False
    is_anonymous: bool = False
    # Embedding and description pipeline status — None means not yet processed
    # (unchanged functions that skipped these stages preserve their Neo4j value).
    # code_embedding_status: "ok" | "skipped" | "context_overflow" | "timeout" | "error"
    # description_status:    "ok" | "skipped" | "invalid_json"     | "timeout" | "error"
    code_embedding_status: str | None = None
    code_embedding_input_chars: int | None = None       # set on failure only
    code_embedding_truncated_chars: int | None = None   # set on failure only
    description_status: str | None = None


@dataclass
class SimilarityEdge:
    """A SIMILAR_TO relationship between two Function nodes."""

    source_id: str               # always the lexicographically smaller id
    target_id: str
    code_similarity: float
    description_similarity: float
    combined_similarity: float
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    database: str
    username: str
    password: str


@dataclass(frozen=True)
class SimilarityConfig:
    threshold: float = 0.82
    top_n: int = 20
    code_weight: float = 0.70
    description_weight: float = 0.30


@dataclass(frozen=True)
class ConcurrencyConfig:
    """Max simultaneous Ollama requests per stage."""
    embed_code: int = 4
    embed_description: int = 4
    describe: int = 2


@dataclass(frozen=True)
class BatchSizeConfig:
    """Neo4j UNWIND batch sizes."""
    function_upsert: int = 50
    edge_upsert: int = 200


@dataclass(frozen=True)
class ReporterConfig:
    cluster_threshold: float = 0.92
    arch_coupling_threshold: float = 0.60
    test_pollution_threshold: int = 5
    timezone: str = "UTC"
    top_n: int = 20
    max_embedding_failures: int = 200
    high_dup_min_cluster_size: int = 3
    high_dup_min_score: float = 0.95
    min_coupling_edges: int = 5
    max_coupling_files_listed: int = 5
    sim_dist_bin_high: float = 0.95
    sim_dist_bin_mid: float = 0.90
    sim_dist_bin_low: float = 0.80
    cohesion_low_threshold: float = 0.30
    cohesion_min_functions: int = 2
    max_cohesion_files_listed: int = 20
    max_isolated_listed: int = 50
    god_file_threshold: int = 20
    cohesion_max_functions: int = 5000


@dataclass(frozen=True)
class LimitsConfig:
    """Source text truncation limits and embedding context window."""
    max_code_chars: int = 22_000
    max_description_source_chars: int = 12_000
    embedding_num_ctx: int = 8192
    context_overflow_char_threshold: int = 10_000
    min_loc_threshold: int = 0   # 0 = disabled; functions below this LOC are skipped


@dataclass(frozen=True)
class PipelineConfig:
    repo_path: str
    repo_name: str
    supported_languages: list[str]
    ignore_paths: list[str]
    embedding_model: str
    embedding_url: str
    allow_gpu: bool
    chat_model: str
    describer_model: str
    similarity: SimilarityConfig
    neo4j: Neo4jConfig
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    batch_sizes: BatchSizeConfig = field(default_factory=BatchSizeConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    reporter: ReporterConfig = field(default_factory=ReporterConfig)
    test_patterns: list[str] = field(default_factory=lambda: ["tests/", "test_", "_test.py"])
    include_tests_in_graph: bool = False
    ignore_anonymous_callbacks: bool = True
    repo_url: str = ""
    base_branch: str = "main"
    git_sync_path: str = ""      # canonical local_path from config; unaffected by --path override
    git_username: str = ""
    git_token: str = ""


@dataclass
class PipelineResult:
    """Summary of a completed pipeline run."""

    total_extracted: int = 0
    loc_filtered: int = 0
    changed: int = 0
    unchanged: int = 0
    newly_deleted: int = 0
    edges_written: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
