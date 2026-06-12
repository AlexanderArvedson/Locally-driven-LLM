# Dependencies

This repository is defined as a Python 3.12+ project in `pyproject.toml` and is intended to be installed with `uv`.

## Install

Install the full project, including development and tool dependencies:

```bash
uv sync --all-extras
```

If you only want the runtime dependencies:

```bash
uv sync
```

If you want a specific extra:

```bash
uv sync --extra dev
uv sync --extra tools
```

## System prerequisites

Some dependencies include native extensions and may need OS build tools before `uv sync` or `uv add` can succeed.

If you see `fatal error: Python.h: No such file or directory`, install the Python development headers for your OS, plus a C/C++ build toolchain.

Typical Linux packages:

- Debian/Ubuntu: `build-essential python3-dev pkg-config`
- Fedora/RHEL/CentOS: `gcc gcc-c++ make python3-devel pkgconf-pkg-config`
- Alpine: `build-base python3-dev pkgconf`

Helpful general-purpose tools:

- `git` for source control and VCS-based installs
- `cmake` if a transitive build step requires it

On macOS, install Xcode command line tools with `xcode-select --install`.

On Windows, use a Python distribution with matching build tools available, or work inside WSL for the smoothest experience.

## Declared project dependencies

The following dependencies are currently declared in `pyproject.toml`.

### Base runtime dependencies

- `fastapi>=0.136.1` - API/server support
- `python-multipart>=0.0.20` - required by FastAPI for parsing `application/x-www-form-urlencoded` and multipart form bodies (Slack slash command payloads)
- `httpx>=0.28.1` - HTTP client used for API calls and test stubs
- `langgraph>=1.2.1` - graph-based workflow orchestration
- `loguru>=0.7.3` - structured logging
- `neo4j>=5.0` - async Neo4j driver used by the embedding pipeline to store function nodes and similarity edges
- `numpy>=1.26` - vectorised cosine similarity matrix computation in the similarity stage
- `pydantic>=2.13.4` - data validation and settings models
- `python-dotenv>=1.2.2` - environment variable loading
- `tenacity>=9.1.4` - retry logic
- `tree-sitter>=0.22` - AST parsing core, used by both the retrieval slicer and the embedding pipeline extractor
- `tree-sitter-python>=0.23` - Python grammar for tree-sitter
- `tree-sitter-typescript>=0.23` - TypeScript and JavaScript grammar for tree-sitter, used by the embedding pipeline
- `uvicorn[standard]>=0.47.0` - ASGI server for local execution

### Development extra

- `pytest>=9.0.3` - test runner
- `pytest-asyncio>=1.4.0` - async test support
- `ruff>=0.15.14` - linting and formatting

### Tools extra

- `graphifyy>=0.8.22` - graph/indexing support as currently declared in the project file

## Notes

- If you intended to depend on the `graphify` package rather than `graphifyy`, update `pyproject.toml` separately before syncing.
- The repo also uses the standard library, so no extra third-party packages are required beyond the list above.