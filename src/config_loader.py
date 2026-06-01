"""Centralized configuration loader for the project.

Configuration is loaded from the local `config.json` file at the repository
root. The file is intentionally ignored by git so each checkout can keep
its own runtime settings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"


@dataclass(frozen=True)
class ModelConfig:
    """Inference settings for a single named model role.

    Attributes:
        name: Model identifier as understood by the provider.
        provider: Provider key (e.g. ``"ollama"``, ``"openai"``).
        api_key: Optional bearer token for API-key based providers.
        url: Optional base URL for self-hosted providers.
        temperature: Sampling temperature passed to the provider when non-null.
            When ``None`` the parameter is omitted from the request entirely.
        max_tokens: Maximum tokens the model may generate per request when
            non-null. When ``None`` the parameter is omitted from the request.
        timeout_seconds: Per-request wall-clock timeout. Must be > 0.
    """

    name: str
    provider: str
    api_key: str | None = None
    url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: int = 300


@dataclass(frozen=True)
class GraphConfig:
    """Graph lifecycle settings for a repository.

    Attributes:
        mode: Storage strategy — ``"hybrid"`` prefers repo-local then system,
            ``"system"`` always uses the system store,
            ``"repo_local"`` uses only ``.graphify/`` inside the repo.
        auto_update: When ``True``, the graph is built or rebuilt automatically
            whenever no valid graph exists for the current HEAD SHA.
    """

    mode: str        # "hybrid" | "system" | "repo_local"
    auto_update: bool


@dataclass(frozen=True)
class RetrievalConfig:
    """Controls how many files and tokens the retrieval pipeline may assemble.

    Attributes:
        max_context_files: Hard cap on the number of files included in the
            assembled retrieval context. Must be > 0.
        max_context_tokens: Hard cap on the estimated token count of the
            assembled retrieval context. Must be > 0.
        limit_reached_behavior: Action taken when a limit is hit:
            ``"ignore"`` silently truncates; ``"warn"`` logs a warning and
            continues; ``"fail"`` aborts retrieval with a ``RuntimeError``.
    """

    max_context_files: int
    max_context_tokens: int
    limit_reached_behavior: str   # "ignore" | "warn" | "fail"


@dataclass(frozen=True)
class SystemConfig:
    """Global system-level settings shared across all repositories.

    Attributes:
        context_path: Root directory for system-managed storage (run history,
            cached graphs, etc.). Supports ``~`` expansion.
    """

    context_path: str  # e.g. "~/.graphify-system"


@dataclass(frozen=True)
class RepositoryConfig:
    name: str
    url: str
    base_branch: str
    prefix: str
    local_path: str
    created_at: str | None
    updated_at: str | None
    max_workflow_revision_cycles: int
    semantic_threshold: float
    graph: GraphConfig
    retrieval: RetrievalConfig
    credentials: dict[str, str] | None
    models: dict[str, ModelConfig]
    slack_webhook_url: str | None


@dataclass(frozen=True)
class AppConfig:
    cron: str
    system: SystemConfig
    repositories: tuple[RepositoryConfig, ...]


def _raise_invalid_field(source: Path, field_name: str) -> None:
    raise ValueError(f"Missing or invalid value for {field_name!r} in {source}")


def _require_str(data: dict[str, Any], key: str, *, source: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid string value for {key!r} in {source}")
    return value


def _require_int(data: dict[str, Any], key: str, *, source: Path) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Missing or invalid integer value for {key!r} in {source}")
    return value


def _load_model_config(raw: dict[str, Any], *, source: Path) -> ModelConfig:
    """Parse a single model role entry from config, validating inference fields."""
    temperature_raw = raw.get("temperature")
    temperature: float | None = None
    if temperature_raw is not None:
        if not isinstance(temperature_raw, (int, float)):
            raise ValueError(f"'temperature' must be a number or null in {source}")
        temperature = float(temperature_raw)
        if temperature < 0:
            raise ValueError(f"'temperature' must be >= 0 in {source}")

    max_tokens_raw = raw.get("max_tokens")
    max_tokens: int | None = None
    if max_tokens_raw is not None:
        if not isinstance(max_tokens_raw, int):
            raise ValueError(f"'max_tokens' must be an integer or null in {source}")
        if max_tokens_raw <= 0:
            raise ValueError(f"'max_tokens' must be > 0 when provided in {source}")
        max_tokens = max_tokens_raw

    timeout_raw = raw.get("timeout_seconds", 300)
    if not isinstance(timeout_raw, int) or timeout_raw <= 0:
        raise ValueError(f"'timeout_seconds' must be a positive integer in {source}")

    return ModelConfig(
        name=_require_str(raw, "name", source=source),
        provider=_require_str(raw, "provider", source=source),
        api_key=raw.get("api_key") if raw.get("api_key") is None or isinstance(raw.get("api_key"), str) else _raise_invalid_field(source, "api_key"),
        url=raw.get("url") if raw.get("url") is None or isinstance(raw.get("url"), str) else _raise_invalid_field(source, "url"),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_raw,
    )


def _load_graph_config(raw: dict[str, Any], *, source: Path) -> GraphConfig:
    """Parse the ``graph`` sub-object from a repository config entry.

    Defaults to ``mode="hybrid"`` and ``auto_update=True`` when fields are
    absent, so existing configs without a ``graph`` block continue to work.
    Raises ``ValueError`` for unrecognised mode values or non-boolean
    ``auto_update``.
    """
    mode = raw.get("mode", "hybrid")
    if mode not in ("hybrid", "system", "repo_local"):
        raise ValueError(f"Invalid graph.mode {mode!r} in {source}; must be 'hybrid', 'system', or 'repo_local'")
    auto_update = raw.get("auto_update", True)
    if not isinstance(auto_update, bool):
        raise ValueError(f"Invalid graph.auto_update in {source}; must be a boolean")
    return GraphConfig(mode=mode, auto_update=auto_update)


def _load_retrieval_config(raw: dict[str, Any], *, source: Path) -> RetrievalConfig:
    """Parse the ``retrieval`` sub-object from a repository config entry.

    All fields have defaults so existing configs without a ``retrieval`` block
    continue to load. Raises ``ValueError`` for out-of-range or unrecognised
    values.
    """
    max_context_files = raw.get("max_context_files", 20)
    if not isinstance(max_context_files, int) or max_context_files <= 0:
        raise ValueError(f"'retrieval.max_context_files' must be a positive integer in {source}")

    max_context_tokens = raw.get("max_context_tokens", 12000)
    if not isinstance(max_context_tokens, int) or max_context_tokens <= 0:
        raise ValueError(f"'retrieval.max_context_tokens' must be a positive integer in {source}")

    limit_reached_behavior = raw.get("limit_reached_behavior", "warn")
    if limit_reached_behavior not in ("ignore", "warn", "fail"):
        raise ValueError(
            f"'retrieval.limit_reached_behavior' must be one of 'ignore', 'warn', 'fail' in {source}"
        )

    return RetrievalConfig(
        max_context_files=max_context_files,
        max_context_tokens=max_context_tokens,
        limit_reached_behavior=limit_reached_behavior,
    )


def _load_system_config(raw: dict[str, Any]) -> SystemConfig:
    """Parse the top-level ``system`` block from config.json.

    Falls back to ``"~/.graphify-system"`` if the block or the
    ``context_path`` key is absent, preserving backwards compatibility with
    configs written before the system block was introduced.
    """
    system_raw = raw.get("system", {})
    context_path = system_raw.get("context_path", "~/.graphify-system")
    if not isinstance(context_path, str) or not context_path.strip():
        context_path = "~/.graphify-system"
    return SystemConfig(context_path=context_path)


def _load_repository_config(raw: dict[str, Any], *, source: Path) -> RepositoryConfig:
    models_raw = raw.get("models")
    if not isinstance(models_raw, dict):
        raise ValueError(f"Missing or invalid object value for 'models' in {source}")

    models: dict[str, ModelConfig] = {}
    for model_name, model_raw in models_raw.items():
        if not isinstance(model_raw, dict):
            raise ValueError(f"Missing or invalid object value for models[{model_name!r}] in {source}")
        models[model_name] = _load_model_config(model_raw, source=source)

    credentials_raw = raw.get("credentials")
    if credentials_raw is not None and not isinstance(credentials_raw, dict):
        raise ValueError(f"Missing or invalid object value for 'credentials' in {source}")
    if isinstance(credentials_raw, dict) and "git" in credentials_raw:
        git_creds = credentials_raw["git"]
        if not isinstance(git_creds, dict):
            raise ValueError(f"Missing or invalid object value for 'credentials.git' in {source}")
        credentials_raw = git_creds

    integrations = raw.get("integrations", {})
    slack_webhook_url = raw.get("slack_webhook_url") or (integrations.get("slack_webhook_url") if isinstance(integrations, dict) else None)
    if slack_webhook_url is not None and not isinstance(slack_webhook_url, str):
        _raise_invalid_field(source, "slack_webhook_url")

    max_workflow_revision_cycles = _require_int(raw, "max_workflow_revision_cycles", source=source)
    if max_workflow_revision_cycles < 1:
        raise ValueError(f"'max_workflow_revision_cycles' must be >= 1 in {source}")

    return RepositoryConfig(
        name=_require_str(raw, "name", source=source),
        url=_require_str(raw, "url", source=source),
        base_branch=_require_str(raw, "base_branch", source=source),
        prefix=_require_str(raw, "prefix", source=source),
        local_path=_require_str(raw, "local_path", source=source),
        created_at=raw.get("created_at") if raw.get("created_at") is None or isinstance(raw.get("created_at"), str) else _raise_invalid_field(source, "created_at"),
        updated_at=raw.get("updated_at") if raw.get("updated_at") is None or isinstance(raw.get("updated_at"), str) else _raise_invalid_field(source, "updated_at"),
        max_workflow_revision_cycles=max_workflow_revision_cycles,
        semantic_threshold=float(raw.get("semantic_threshold", 0.75)),
        graph=_load_graph_config(raw.get("graph", {}), source=source),
        retrieval=_load_retrieval_config(raw.get("retrieval", {}), source=source),
        credentials=credentials_raw,
        models=models,
        slack_webhook_url=slack_webhook_url,
    )


def _select_primary_model(models: dict[str, ModelConfig]) -> ModelConfig:
    for key in ("LLM", "Coder", "coder", "chat-model"):
        if key in models:
            return models[key]
    return next(iter(models.values()))


def get_repository_config(repo_path: str | None = None) -> RepositoryConfig:
    """Return the configured repository that best matches `repo_path`.

    If no repo path is supplied, or no configured repository matches, the
    first configured repository is used as the default.
    """
    if repo_path:
        resolved_repo_path = Path(repo_path).resolve()
        for repository in APP_CONFIG.repositories:
            try:
                if resolved_repo_path == Path(repository.local_path).resolve():
                    return repository
            except OSError:
                if repo_path == repository.local_path:
                    return repository

    return APP_CONFIG.repositories[0]


def get_primary_model(repo_path: str | None = None) -> ModelConfig:
    return _select_primary_model(get_repository_config(repo_path).models)


def get_coder_model_config(repo_path: str | None = None) -> ModelConfig:
    """Return the full ModelConfig for the coder role."""
    return _select_primary_model(get_repository_config(repo_path).models)


def get_semantic_model_config(repo_path: str | None = None) -> ModelConfig:
    """Return the full ModelConfig for the semantic validator role.

    Prefers models["semantic_validator"], then falls back to models["reviewer"]
    (the legacy key), then to the primary model.
    """
    models = get_repository_config(repo_path).models
    for key in ("semantic_validator", "reviewer"):
        if key in models:
            return models[key]
    return get_primary_model(repo_path)


def get_ollama_base_url(repo_path: str | None = None) -> str:
    model = get_primary_model(repo_path)
    if not model.url:
        raise ValueError("Primary model is missing a URL in config.json")
    return model.url


def get_coder_model(repo_path: str | None = None) -> str:
    return get_primary_model(repo_path).name


def get_max_workflow_revision_cycles(repo_path: str | None = None) -> int:
    """Return the maximum number of workflow revision cycles allowed."""
    return get_repository_config(repo_path).max_workflow_revision_cycles


def get_retrieval_config(repo_path: str | None = None) -> RetrievalConfig:
    """Return retrieval limits and behavior for the repository matching ``repo_path``."""
    return get_repository_config(repo_path).retrieval


def get_semantic_threshold(repo_path: str | None = None) -> float:
    """Return the minimum task_alignment_score required for semantic_validator to pass."""
    return get_repository_config(repo_path).semantic_threshold


def get_semantic_model(repo_path: str | None = None) -> str:
    """Return the model name for the semantic validator.

    Prefers models["semantic_validator"], then falls back to models["reviewer"]
    (the legacy key), then to the primary model.
    """
    return get_semantic_model_config(repo_path).name


def get_graph_config(repo_path: str | None = None) -> GraphConfig:
    """Return the graph lifecycle config for the repository matching ``repo_path``.

    Falls back to the first configured repository when no match is found.
    """
    return get_repository_config(repo_path).graph


def get_system_context_path() -> Path:
    """Return the expanded absolute path for the system-level context store.

    Resolves the ``system.context_path`` value from config.json with ``~``
    expansion applied.
    """
    return Path(APP_CONFIG.system.context_path).expanduser()


EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.example.json"


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or CONFIG_PATH
    if not path.exists():
        if config_path is not None:
            # Caller requested a specific path that doesn't exist — always an error.
            raise FileNotFoundError(f"Missing required config file: {path}")
        # config.json absent (CI, fresh checkout): fall back to the tracked example
        # file so the module imports cleanly without a local config.
        if EXAMPLE_CONFIG_PATH.exists():
            path = EXAMPLE_CONFIG_PATH
        else:
            raise FileNotFoundError(f"Missing required config file: {CONFIG_PATH}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")

    repositories_raw = raw.get("repositories")
    if not isinstance(repositories_raw, list) or not repositories_raw:
        raise ValueError(f"Missing or invalid list value for 'repositories' in {path}")

    repositories = []
    for repository_raw in repositories_raw:
        if not isinstance(repository_raw, dict):
            raise ValueError(f"Each repository entry must be a JSON object in {path}")
        repositories.append(_load_repository_config(repository_raw, source=path))

    return AppConfig(
        cron=_require_str(raw, "cron", source=path),
        system=_load_system_config(raw),
        repositories=tuple(repositories),
    )


APP_CONFIG: Final[AppConfig] = load_config()

OLLAMA_BASE_URL: Final[str] = get_ollama_base_url()
CODER_MODEL: Final[str] = get_coder_model()
MAX_WORKFLOW_REVISION_CYCLES: Final[int] = get_max_workflow_revision_cycles()


def update_repository_timestamps(
    repo_name: str,
    *,
    created_at: str | None = None,
    updated_at: str | None = None,
    config_path: Path | None = None,
) -> None:
    """Persist ``created_at`` and/or ``updated_at`` for a repository in config.json.

    Reads the raw JSON, patches only the supplied fields, and writes the file
    back atomically. The in-memory ``APP_CONFIG`` is intentionally left stale
    because timestamps are write-once metadata, not runtime-critical values.
    """
    path = config_path or CONFIG_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))

    for repo in raw.get("repositories", []):
        if repo.get("name") == repo_name:
            if created_at is not None and not repo.get("created_at"):
                repo["created_at"] = created_at
            if updated_at is not None:
                repo["updated_at"] = updated_at
            break

    path.write_text(json.dumps(raw, indent=4, ensure_ascii=False), encoding="utf-8")
