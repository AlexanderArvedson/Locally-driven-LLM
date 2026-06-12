# Pulling Ollama models

The pipeline uses two types of model, configured separately in `config.json`. Both must be pulled into Ollama before the first run.

---

## Why two types?

**Embedding model** (`models.embedding`) — converts function source code and descriptions into fixed-size numeric vectors. These vectors are stored in Neo4j and used to compute similarity between functions. Must be a dedicated embedding model.

**Description model** (`models.describer`) — generates a structured JSON description (summary, inputs, outputs, side effects) for each function. Falls back to `models.chat` if `describer` is absent. Only called when running without `--no-descriptions`.

---

## Pull the default models

The defaults in `config.example.json` are `nomic-embed-text` (embedding) and `qwen2.5-coder:7b` (describer/chat). The other model roles in `config.json` (`coder`, `semantic_validator`, `reporter`) belong to the agent workflow which is not in use — they can stay at the defaults.

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

**For `models.describer` / `models.chat`**: any capable instruction-tuned model works. `qwen2.5-coder` variants are well-suited for code-heavy tasks. `llama3`, `mistral`, and `deepseek-coder` are popular general-purpose alternatives. Larger models produce better descriptions but run slower.

Once you have decided on a model, pull it and update `models.embedding` or `models.describer` in `config.json` with its exact name as shown on the library page.

> **Important**: Never use a chat model for `models.embedding`. Chat models do not produce the fixed-dimension dense vectors the pipeline expects — Ollama will return an error at runtime. Always use a model listed under the Embedding tag for that role.

---

→ Next: [Running the pipeline](running-the-pipeline.md)
