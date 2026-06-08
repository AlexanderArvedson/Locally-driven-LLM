# Pulling Ollama models

The pipeline uses two types of model, configured separately in `config.json`. Both must be pulled into Ollama before the first run.

---

## Why two types?

**Embedding model** (`models.embedding`) — converts function source code and descriptions into fixed-size numeric vectors. These vectors are stored in Neo4j and used to compute similarity between functions. Must be a dedicated embedding model.

**Chat/coder models** (`models.chat`, `models.coder`, `models.describer`, `models.semantic_validator`) — used for generating structured JSON descriptions of each function and for code tasks. Can all point to the same model.

---

## Pull the default models

The defaults in `config.example.json` are `nomic-embed-text` (embedding) and `qwen2.5-coder:7b` (chat/coder).

**If Ollama is running inside Docker** (the default after the previous step):

```bash
docker exec my_ollama ollama pull nomic-embed-text
docker exec my_ollama ollama pull qwen2.5-coder:7b
```

**If Ollama is running directly on your machine** (not via Docker):

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5-coder:7b
```

Pulls can take a few minutes depending on model size and connection speed. `qwen2.5-coder:7b` is approximately 4.7 GB.

---

## Using different models

Browse [ollama.com/library](https://ollama.com/library) to find alternatives.

**For `models.embedding`**: filter by the **Embedding** tag. Only models under this tag produce the dense fixed-dimension vectors the pipeline expects. `nomic-embed-text` (274 MB) and `mxbai-embed-large` (670 MB) are common choices.

**For chat/coder roles**: any capable instruction-tuned model works. `qwen2.5-coder` variants are well-suited for code-heavy tasks. `llama3`, `mistral`, and `deepseek-coder` are popular general-purpose alternatives. Larger models produce better descriptions but run slower.

Once you have decided on a model, pull it and update the relevant `models.*` entry in `config.json` with its exact name as shown on the library page.

> **Important**: Never use a chat model for `models.embedding`. Chat models do not produce the fixed-dimension dense vectors the pipeline expects — Ollama will return an error at runtime. Always use a model listed under the Embedding tag for that role.

---

→ Next: [Running the pipeline](running-the-pipeline.md)
