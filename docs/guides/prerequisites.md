# Prerequisites

Before setting up the pipeline you need two tools installed on your machine.

---

## Docker and Docker Compose v2

Docker runs the infrastructure services (Ollama and Neo4j). Docker Compose v2 is the `docker compose` subcommand (note: no hyphen) bundled with Docker Desktop and recent Docker Engine installations.

- [Install Docker Desktop](https://docs.docker.com/get-docker/) (Mac, Windows, Linux) — includes Compose v2.
- On Linux without Docker Desktop: install [Docker Engine](https://docs.docker.com/engine/install/) and the [Compose plugin](https://docs.docker.com/compose/install/linux/) separately.

Verify after installation:

```bash
docker --version
docker compose version
```

---

## uv

`uv` is the Python package manager used to run the pipeline CLI.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via pip:

```bash
pip install uv
```

Verify:

```bash
uv --version
```

---

→ Next: [Configuration](configuration.md)
