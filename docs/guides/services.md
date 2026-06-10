# Starting services

The pipeline needs Ollama (model inference) and Neo4j (graph database) running before it can do anything. Both are managed via Docker Compose.

---

## Start Ollama and Neo4j

```bash
docker compose up -d ollama neo4j
```

The `-d` flag runs them in the background. The first start will pull the Docker images, which may take a minute.

To check that both containers are up:

```bash
docker compose ps
```

Both should show `running`.

---

## Starting the FastAPI service

The FastAPI service is required for scheduled pipeline runs and the REST API. Start it alongside the other services:

```bash
docker compose up -d ollama neo4j fastapi
```

---

## GPU acceleration (Nvidia only)

By default, Ollama runs on CPU. If you have an Nvidia GPU you can enable hardware acceleration by appending the GPU override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d ollama neo4j
```

To include the FastAPI service at the same time:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d ollama neo4j fastapi
```

This requires the [Nvidia Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) to be installed on your host. Without it, Docker will fail to start the container with a device error.

The base `docker-compose.yml` works on any machine without modification. The GPU override is strictly opt-in.

---

## Using an external Neo4j instance

If you are pointing to a self-hosted or cloud Neo4j instance instead of the bundled container, ensure the **APOC plugin** is installed. The pipeline's schema stage uses APOC procedures to create vector indexes. The bundled `neo4j` container installs APOC automatically via `NEO4J_PLUGINS` in `docker-compose.yml`.

Update `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` in `.env` to point at your instance.

---

→ Next: [Pulling models](models.md)
