# Function Embedding and Similarity Pipeline

The pipeline subsystem scans a source code repository, extracts every function and method as standalone text, generates vector embeddings and LLM descriptions for each one, stores the results in Neo4j, and builds a weighted similarity graph between related functions.

It is a standalone subsystem under `src/pipeline/` and shares no code with the LangGraph workflow under `src/graph/`. The only shared dependency is `src/core/ollama_client.py`.

---

## How it works

The pipeline runs twelve sequential stages:

1. **ensure_schema** — creates Neo4j constraints, property indexes, and vector indexes if they do not already exist.
2. **extract** — walks the repository with tree-sitter, extracting every function and method as a `FunctionRecord` with source text, line numbers, language, and class membership.
3. **get_existing_hashes** — fetches `{id: sourceHash}` for all live functions already in Neo4j.
4. **partition** — splits extracted records into _changed_ (new or source-modified) and _unchanged_ (hash matches Neo4j).
5. **embed_code** — sends each changed function's source code to the Ollama embedding model. Unchanged functions skip this stage.
6. **describe** — sends each changed function to the Ollama chat model, requesting a structured JSON description (summary, inputs, outputs, side effects, errors, dependencies). Skipped when `--no-descriptions` is passed.
7. **embed_description** — embeds the `summary` field of each generated description. Skipped with `--no-descriptions`.
8. **upsert_functions** — writes all function nodes to Neo4j via `MERGE` on stable ID. Unchanged functions have their `lastSeenAt` updated; everything else is overwritten.
9. **soft_delete** — marks any function previously seen in this repo but absent from the current scan as `isDeleted: true`.
10. **get_all_embeddings** — fetches all live code embeddings back from Neo4j for similarity computation.
11. **compute_similarity** — builds an N×N cosine similarity matrix using numpy, filters to top-N neighbours per function above the configured threshold, and produces `SimilarityEdge` records.
12. **upsert_edges** — deletes all existing `SIMILAR_TO` edges for the repo and re-inserts the freshly computed set so stale edges from changed functions do not persist.

---

## Running the pipeline

```bash
# Full run (embedding + descriptions + similarity graph)
uv run run_pipeline.py

# Skip LLM descriptions — much faster, code-embedding similarity only
uv run run_pipeline.py --no-descriptions

# Target a specific subfolder instead of the whole repo
uv run run_pipeline.py --path /path/to/monorepo/apps/backend --no-descriptions

# Validate extraction counts without touching Neo4j or Ollama
uv run run_pipeline.py --dry-run

# Generate a markdown report from the current Neo4j graph without re-running
uv run run_pipeline.py --report-only

# Run the pipeline and generate a report at the end
uv run run_pipeline.py --no-descriptions --report

# Use a specific repository entry from config.json
uv run run_pipeline.py --repo my-other-repo
```

### Options

| Flag | Description |
|---|---|
| `--config PATH` | Path to `config.json`. Defaults to `./config.json`. |
| `--repo NAME` | Repository name to use from `config.json`. Defaults to the first entry. |
| `--path PATH` | Override `repo_path` from config. Useful for targeting a subfolder. |
| `--dry-run` | Extract functions and query Neo4j for hashes, but skip all Ollama calls and Neo4j writes. |
| `--no-descriptions` | Skip LLM description generation and description embeddings. Recommended for first runs on large repositories. |
| `--report` | Generate a markdown similarity report after the pipeline completes. |
| `--report-only` | Skip the pipeline entirely and generate a report from the current Neo4j graph. |

---

## Supported languages

| Language | Extensions |
|---|---|
| Python | `.py` |
| TypeScript | `.ts`, `.tsx` |
| JavaScript | `.js`, `.jsx` |

Languages are configured per repository in `config.json` under `repositories[].pipeline.supported_languages`. Files with unsupported extensions are silently skipped.

---

## Incremental processing

The pipeline avoids redundant Ollama calls using `sourceHash` — a SHA-256 of the raw function source text.

On each run:
- Functions whose hash matches what is stored in Neo4j are skipped for embedding and description.
- Functions that are new or changed are fully re-processed.
- Functions present in the previous scan but missing from the current one are soft-deleted (`isDeleted: true`).

Similarity edges are always recomputed from scratch to ensure stale edges from changed functions are removed.

---

## Neo4j graph model

### Node: `Function`

One node per extracted function or method.

| Property | Type | Description |
|---|---|---|
| `id` | string | SHA-256 of `repo:filePath:qualifiedName:startLine`. Stable across re-scans when source is unchanged. |
| `repo` | string | Repository name from config. |
| `language` | string | Programming language (`python`, `typescript`, `javascript`). |
| `filePath` | string | Relative path from repo root. |
| `functionName` | string | Bare function or method name. |
| `qualifiedName` | string | `ClassName.methodName` for methods, bare name for top-level functions. |
| `className` | string \| null | Enclosing class name, if applicable. |
| `startLine` | integer | 1-indexed start line of the function body. |
| `endLine` | integer | 1-indexed end line of the function body. |
| `sourceCode` | string | Raw function source text (truncated at `pipeline.limits.max_code_chars` characters before embedding; default 22 000). |
| `sourceHash` | string | SHA-256 of `sourceCode`. Used for incremental skip logic. |
| `description` | string \| null | JSON string with keys `summary`, `inputs`, `outputs`, `sideEffects`, `errors`, `dependencies`. Null when `--no-descriptions` was used or description generation failed. |
| `codeEmbedding` | list\<float\> \| null | Embedding vector of source code. Null if embedding failed. |
| `descriptionEmbedding` | list\<float\> \| null | Embedding vector of the description summary. Null when descriptions are skipped or failed. |
| `createdAt` | string | ISO-8601 timestamp of first insertion. Preserved on re-runs. |
| `updatedAt` | string | ISO-8601 timestamp of most recent change. |
| `lastSeenAt` | string | ISO-8601 timestamp of the most recent scan that included this function. Used to detect deletions. |
| `isDeleted` | boolean | `true` if the function was absent from the most recent scan. |

### Relationship: `SIMILAR_TO`

Directed edge between two `Function` nodes. Only created when `source.id < target.id` to avoid duplicate pairs.

| Property | Type | Description |
|---|---|---|
| `codeSimilarity` | float | Cosine similarity between the two `codeEmbedding` vectors. |
| `descriptionSimilarity` | float | Cosine similarity between the two `descriptionEmbedding` vectors. `0.0` when descriptions are absent. |
| `combinedSimilarity` | float | Weighted combination: `code_weight × codeSimilarity + description_weight × descriptionSimilarity`. Falls back to `codeSimilarity` when description embeddings are absent. |
| `updatedAt` | string | ISO-8601 timestamp of last update. |

### Indexes

The following are created automatically on first run by `ensure_schema`:

- Uniqueness constraint on `Function.id`
- Property index on `Function.repo`
- Property index on `Function.filePath`
- Property index on `Function.functionName`
- Vector index on `Function.codeEmbedding` (cosine, dimension inferred from first embedding)
- Vector index on `Function.descriptionEmbedding` (cosine, same dimension)

---

## Report generation

`--report` and `--report-only` write a markdown file to the project root named `pipeline-report-<timestamp>.md`. The report includes:

- Summary statistics (function count, edge count, isolated functions)
- Language breakdown
- Top 20 most similar function pairs (near-duplicates / shared logic candidates)
- Top 20 most-connected functions (utility or pattern code reused across the codebase)
- Top 20 files by edge count

---

## Querying the graph

Example Cypher queries for the Neo4j browser at `http://localhost:7474`:

```cypher
-- Count all indexed functions and edges
MATCH (f:Function) RETURN count(f) AS functions;
MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS edges;

-- Browse functions in a specific file
MATCH (f:Function)
WHERE f.filePath CONTAINS "EventLoop"
RETURN f.functionName, f.startLine, f.endLine
ORDER BY f.startLine;

-- Find near-duplicates
MATCH (a:Function)-[r:SIMILAR_TO]->(b:Function)
WHERE r.combinedSimilarity > 0.95
RETURN a.qualifiedName, a.filePath, b.qualifiedName, b.filePath, r.combinedSimilarity
ORDER BY r.combinedSimilarity DESC
LIMIT 20;

-- Visualise the similarity graph
MATCH (a:Function)-[r:SIMILAR_TO]->(b:Function)
WHERE r.combinedSimilarity > 0.88
RETURN a, r, b
LIMIT 100;
```

---

## Source layout

```
src/pipeline/
  contracts.py      — FunctionRecord, SimilarityEdge, PipelineConfig dataclasses
  config.py         — load_pipeline_config(): reads neo4j + pipeline blocks from config.json
  scanner.py        — repo file walker with ignore-path pruning
  extractor.py      — tree-sitter AST traversal, emits FunctionRecord per function
  embedder.py       — EmbeddingService: code and description embedding via OllamaClient
  describer.py      — DescriptionService: LLM JSON description generation via OllamaClient
  similarity.py     — cosine similarity matrix, top-N filtering, SimilarityEdge list
  neo4j_store.py    — Neo4jStore: async driver, MERGE upserts, UNWIND batching
  pipeline.py       — EmbeddingPipeline: orchestrates all twelve stages
  reporter.py       — post-run markdown report generator

run_pipeline.py     — CLI entry point
```
