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
    name: str
    provider: str
    api_key: str | None = None
    url: str | None = None


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
    max_iterations: int
    graph: GraphConfig
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
    return ModelConfig(
        name=_require_str(raw, "name", source=source),
        provider=_require_str(raw, "provider", source=source),
        api_key=raw.get("api_key") if raw.get("api_key") is None or isinstance(raw.get("api_key"), str) else _raise_invalid_field(source, "api_key"),
        url=raw.get("url") if raw.get("url") is None or isinstance(raw.get("url"), str) else _raise_invalid_field(source, "url"),
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

    return RepositoryConfig(
        name=_require_str(raw, "name", source=source),
        url=_require_str(raw, "url", source=source),
        base_branch=_require_str(raw, "base_branch", source=source),
        prefix=_require_str(raw, "prefix", source=source),
        local_path=_require_str(raw, "local_path", source=source),
        created_at=raw.get("created_at") if raw.get("created_at") is None or isinstance(raw.get("created_at"), str) else _raise_invalid_field(source, "created_at"),
        updated_at=raw.get("updated_at") if raw.get("updated_at") is None or isinstance(raw.get("updated_at"), str) else _raise_invalid_field(source, "updated_at"),
        max_iterations=_require_int(raw, "max_iterations", source=source),
        graph=_load_graph_config(raw.get("graph", {}), source=source),
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


def get_ollama_base_url(repo_path: str | None = None) -> str:
    model = get_primary_model(repo_path)
    if not model.url:
        raise ValueError("Primary model is missing a URL in config.json")
    return model.url


def get_coder_model(repo_path: str | None = None) -> str:
    return get_primary_model(repo_path).name


def get_max_iterations(repo_path: str | None = None) -> int:
    return get_repository_config(repo_path).max_iterations


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


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Missing required config file: {path}")

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
MAX_ITERATIONS: Final[int] = get_max_iterations()


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
