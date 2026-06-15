# Prerequisites

Before setting up the pipeline you need three tools installed on your machine.

---

## Git

Git is used to clone the repository.

- [Install Git](https://git-scm.com/downloads) (Mac, Windows, Linux).

Verify after installation:

```bash
git --version
```

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

`uv` is the Python package manager used to run the pipeline CLI. It also manages Python itself — you do not need to install Python separately. uv will automatically download Python 3.12 when you first run the project.

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

## Note: WeasyPrint system libraries

If you plan to run the pipeline **directly on your host machine** (outside Docker), WeasyPrint requires native system libraries (Pango, Cairo, HarfBuzz, fontconfig) for PDF report generation. When running via Docker Compose these are installed automatically.

See [DEPENDENCIES.md](../DEPENDENCIES.md#weasyprint-system-libraries) for the per-OS install commands.

---

→ Next: [Configuration](configuration.md)
