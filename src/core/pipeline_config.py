"""Pipeline configuration loader.

Reads the top-level ``neo4j`` block and the per-repository ``pipeline`` block
from config.json, assembling a ``PipelineConfig`` that combines pipeline-specific
settings with the existing repository model/path fields.

Intentionally does not import from ``src/core/config_loader.py`` or any other
subsystem — the pipeline is self-contained.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.pipeline.contracts import (
    BatchSizeConfig,
    CheckpointConfig,
    ConcurrencyConfig,
    LimitsConfig,
    Neo4jConfig,
    PipelineConfig,
    ReporterConfig,
    SimilarityConfig,
    SlackPipelineConfig,
)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Environment variable {name!r} is required but not set. Add it to your .env file.")
    return value


def _validate_timezone(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError):
        raise ValueError(f"Invalid 'reporter.timezone' value {tz!r}; must be a valid IANA timezone (e.g. 'UTC', 'Europe/Stockholm')")
    return tz


def load_pipeline_config(config_path: str | Path = "config.json", repo_name: str | None = None) -> PipelineConfig:
    """Load pipeline configuration for a repository.

    Args:
        config_path: Path to the JSON config file.
        repo_name: Name of the repository entry to use. When ``None``, the
            first repository in the list is used.

    Raises:
        FileNotFoundError: If the config file does not exist.
        KeyError: If required fields are missing.
        ValueError: If no matching repository is found.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open() as f:
        raw = json.load(f)

    repos: list[dict] = raw.get("repositories", [])
    if not repos:
        raise ValueError("No repositories configured in config.json")

    if repo_name is not None:
        repo = next((r for r in repos if r.get("name") == repo_name), None)
        if repo is None:
            raise ValueError(f"Repository '{repo_name}' not found in config.json")
    else:
        repo = repos[0]

    models = repo["models"]
    embed_model = models["embedding"]
    chat_model = models["chat"]
    describer_model = models.get("describer") or chat_model

    pipeline_block = repo.get("pipeline", {})
    sim_block = pipeline_block.get("similarity", {})
    concurrency_block = pipeline_block.get("concurrency", {})
    batch_block = pipeline_block.get("batch_sizes", {})
    limits_block = pipeline_block.get("limits", {})
    reporter_block = pipeline_block.get("reporter", {})
    slack_block = pipeline_block.get("slack", {})
    checkpoint_block = pipeline_block.get("checkpoint", {})

    return PipelineConfig(
        repo_path=repo["local_path"],
        repo_name=repo["name"],
        supported_languages=pipeline_block.get("supported_languages", ["python"]),
        ignore_paths=pipeline_block.get("ignore_paths", [".venv", "node_modules", "__pycache__", ".git"]),
        embedding_model=embed_model["name"],
        embedding_url=os.environ.get("OLLAMA_URL") or embed_model.get("url", "http://localhost:11434"),
        allow_gpu=embed_model.get("allow_gpu", True),
        chat_model=chat_model["name"],
        describer_model=describer_model["name"],
        similarity=SimilarityConfig(
            threshold=sim_block.get("threshold", 0.82),
            top_n=sim_block.get("top_n", 20),
            code_weight=sim_block.get("code_weight", 0.70),
            description_weight=sim_block.get("description_weight", 0.30),
        ),
        neo4j=Neo4jConfig(
            uri=_require_env("NEO4J_URI"),
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
            username=_require_env("NEO4J_USERNAME"),
            password=_require_env("NEO4J_PASSWORD"),
        ),
        concurrency=ConcurrencyConfig(
            embed_code=concurrency_block.get("embed_code", 4),
            embed_description=concurrency_block.get("embed_description", 4),
            describe=concurrency_block.get("describe", 2),
        ),
        batch_sizes=BatchSizeConfig(
            function_upsert=batch_block.get("function_upsert", 50),
            edge_upsert=batch_block.get("edge_upsert", 200),
        ),
        limits=LimitsConfig(
            max_code_chars=limits_block.get("max_code_chars", 22_000),
            max_description_source_chars=limits_block.get("max_description_source_chars", 12_000),
            context_overflow_char_threshold=limits_block.get("context_overflow_char_threshold", 10_000),
            min_loc_threshold=limits_block.get("min_loc_threshold", 0),
        ),
        embedding_num_ctx=embed_model.get("num_ctx") or 8192,
        embedding_timeout_seconds=embed_model.get("timeout_seconds", 300),
        describe_num_ctx=describer_model.get("num_ctx") or 8192,
        describe_timeout_seconds=describer_model.get("timeout_seconds", 900),
        describer_temperature=describer_model.get("temperature"),
        describer_max_tokens=describer_model.get("max_tokens"),
        describer_allow_gpu=describer_model.get("allow_gpu", True),
        test_patterns=pipeline_block.get("test_patterns", ["tests/", "test_", "_test.py"]),
        include_tests_in_graph=pipeline_block.get("include_tests_in_graph", False),
        ignore_anonymous_callbacks=pipeline_block.get("ignore_anonymous_callbacks", True),
        repo_url=repo.get("url", ""),
        base_branch=repo.get("base_branch", "main"),
        git_sync_path=repo.get("local_path", ""),
        git_username=repo.get("credentials", {}).get("git", {}).get("username", ""),
        git_token=repo.get("credentials", {}).get("git", {}).get("token", ""),
        slack=SlackPipelineConfig(
            enabled=slack_block.get("enabled", True),
            debug_messages=slack_block.get("debug_messages", False),
            progress_update_interval=slack_block.get("progress_update_interval", 100),
        ),
        checkpoint=CheckpointConfig(
            enabled=checkpoint_block.get("enabled", True),
            interval=checkpoint_block.get("interval", 10),
            directory=checkpoint_block.get("directory", ".pipeline_checkpoints"),
        ),
        reporter=ReporterConfig(
            cluster_threshold=reporter_block.get("cluster_threshold", 0.92),
            arch_coupling_threshold=reporter_block.get("arch_coupling_threshold", 0.60),
            test_pollution_threshold=reporter_block.get("test_pollution_threshold", 5),
            timezone=_validate_timezone(reporter_block.get("timezone", "UTC")),
            top_n=reporter_block.get("top_n", 20),
            max_embedding_failures=reporter_block.get("max_embedding_failures", 200),
            high_dup_min_cluster_size=reporter_block.get("high_dup_min_cluster_size", 3),
            high_dup_min_score=reporter_block.get("high_dup_min_score", 0.95),
            min_coupling_edges=reporter_block.get("min_coupling_edges", 5),
            max_coupling_files_listed=reporter_block.get("max_coupling_files_listed", 5),
            sim_dist_bin_high=reporter_block.get("sim_dist_bin_high", 0.95),
            sim_dist_bin_mid=reporter_block.get("sim_dist_bin_mid", 0.90),
            sim_dist_bin_low=reporter_block.get("sim_dist_bin_low", 0.80),
            cohesion_low_threshold=reporter_block.get("cohesion_low_threshold", 0.30),
            cohesion_min_functions=reporter_block.get("cohesion_min_functions", 2),
            max_cohesion_files_listed=reporter_block.get("max_cohesion_files_listed", 20),
            max_isolated_listed=reporter_block.get("max_isolated_listed", 50),
            god_file_threshold=reporter_block.get("god_file_threshold", 20),
            slack_top_n_query=reporter_block.get("slack_top_n_query", 5),
            slack_top_n_report=reporter_block.get("slack_top_n_report", 3),
        ),
    )
