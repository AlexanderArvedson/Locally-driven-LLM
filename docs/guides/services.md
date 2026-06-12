# Starting services

The pipeline needs Ollama (model inference) and Neo4j (graph database) running before it can do anything. Both are managed via Docker Compose.

---

## Start Ollama and Neo4j

```bash
docker compose up --build -d ollama neo4j
```

The `--build` flag rebuilds images if anything has changed. The `-d` flag runs them in the background. The first start will pull the Docker images, which may take a minute.

To see logs in the terminal instead of running in the background, omit `-d`:

```bash
docker compose up --build ollama neo4j
```

To check that both containers are up:

```bash
docker compose ps
```

Both should show `running`.

Once Neo4j is running you can browse the graph at **http://localhost:7474** using the Neo4j Browser UI, you may need to add /browser at the end if it doesn't redirect you automatically. Log in with the `NEO4J_USERNAME` and `NEO4J_PASSWORD` from your `.env` file.

---

## Starting the FastAPI service

The FastAPI service is required for Slack slash commands and scheduled pipeline runs. If you only need to run the pipeline manually from the terminal, you can skip it for now — `uv run run_pipeline.py` works without it.

```bash
docker compose up --build -d ollama neo4j fastapi
```

Omit `-d` to follow logs in the terminal:

```bash
docker compose up --build ollama neo4j fastapi
```

To confirm it is healthy:

```bash
curl http://localhost:8000/health
```

You should receive `{"status":"ok"}`. If you changed `FASTAPI_PORT` in `.env`, substitute that port number.

---

## Two ways to run the pipeline

| Mode | Command | When to use |
|------|---------|-------------|
| **CLI** | `uv run run_pipeline.py` | One-off runs from the terminal. Ollama and Neo4j must be running; the fastapi container is not required. |
| **Server** | `docker compose up fastapi` | Needed for Slack slash commands (`/pipeline`, `/report`, `/query`) and cron-scheduled automatic runs. The fastapi container manages the task queue and keeps a persistent connection to Slack. |

Both modes run the same pipeline logic and write to the same Neo4j database and `run_reports/` directory.

---

## GPU acceleration (Nvidia only)

By default, Ollama runs on CPU. If you have an Nvidia GPU you can enable hardware acceleration by appending the GPU override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d ollama neo4j
```

To include the FastAPI service at the same time:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d ollama neo4j fastapi
```

Omit `-d` from either command to follow logs in the terminal.

This requires the [Nvidia Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) to be installed on your host. Without it, Docker will fail to start the container with a device error.

The base `docker-compose.yml` works on any machine without modification. The GPU override is strictly opt-in.

---

## Using an external Neo4j instance

If you are pointing to a self-hosted or cloud Neo4j instance instead of the bundled container, ensure the **APOC plugin** is installed. The pipeline's schema stage uses APOC procedures to create vector indexes. The bundled `neo4j` container installs APOC automatically via `NEO4J_PLUGINS` in `docker-compose.yml`.

Update `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` in `.env` to point at your instance.

---

← Previous: [Configuration](configuration.md) | → Next: [Pulling models](models.md)
