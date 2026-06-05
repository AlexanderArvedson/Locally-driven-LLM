# Function Embedding and Similarity Pipeline

The pipeline subsystem scans a source code repository, extracts every function and method as standalone text, generates vector embeddings and LLM descriptions for each one, stores the results in Neo4j, and builds a weighted similarity graph between related functions.

It is a standalone subsystem under `src/pipeline/` and shares no code with the LangGraph workflow under `src/graph/`. The only shared dependency is `src/core/ollama_client.py`.

---

## How it works

The pipeline runs thirteen sequential stages:

1. **ensure_schema** — creates Neo4j constraints, property indexes, and vector indexes if they do not already exist.
2. **extract** — walks the repository with tree-sitter, extracting every function and method as a `FunctionRecord` with source text, line numbers, language, and class membership.
3. **loc_filter** — if `pipeline.limits.min_loc_threshold` is greater than `0`, removes any function whose line count (`endLine - startLine + 1`) falls below the threshold. Filtered functions are never embedded, described, or stored. The count is reported in the CLI summary and the report's Graph Overview section. Disabled by default (`0`).
4. **get_existing_hashes** — fetches `{id: sourceHash}` for all live functions already in Neo4j.
5. **partition** — splits extracted records into _changed_ (new or source-modified) and _unchanged_ (hash matches Neo4j).
6. **embed_code** — sends each changed function's source code to the Ollama embedding model. Unchanged functions skip this stage.
7. **describe** — sends each changed function to the Ollama chat model, requesting a structured JSON description (summary, inputs, outputs, side effects, errors, dependencies). Skipped when `--no-descriptions` is passed.
8. **embed_description** — embeds the `summary` field of each generated description. Skipped with `--no-descriptions`.
9. **upsert_functions** — writes all function nodes to Neo4j via `MERGE` on stable ID. Unchanged functions have their `lastSeenAt` updated; everything else is overwritten.
10. **soft_delete** — marks any function previously seen in this repo but absent from the current scan as `isDeleted: true`.
11. **get_all_embeddings** — fetches all live functions that have at least one embedding (code or description) from Neo4j for similarity computation. Functions with only a description embedding (e.g. those whose source code exceeded the embedding model's context window) are included.
12. **compute_similarity** — for each function, queries the Neo4j HNSW vector indexes (`function_code_embedding_index` and/or `function_desc_embedding_index`) to find its top-N nearest neighbours. Up to 20 index queries run concurrently. Candidates from both indexes are merged per target function; the combined score is `code_weight × codeSimilarity + description_weight × descriptionSimilarity` when both signals are available, falling back to the single available signal otherwise. This is O(n log n) rather than O(n²) and avoids building an in-memory similarity matrix.
13. **upsert_edges** — deletes all existing `SIMILAR_TO` edges for the repo and re-inserts the freshly computed set so stale edges from changed functions do not persist.

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

### Running via Slack

The same flags are available through the `/pipeline` slash command when the Slack bot is running:

```
/pipeline
/pipeline --no-descriptions
/pipeline --no-descriptions --report
/pipeline --report-only
/pipeline --dry-run
/pipeline --path /app/subdir --no-descriptions
```

On completion the bot posts a notification to `SLACK_NOTIFY_CHANNEL` if that env var is set. See `docs/SLACK_SETUP.md` for setup instructions.

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
| `codeEmbedding` | list\<float\> \| null | Embedding vector of source code. Null if embedding failed (e.g. source exceeded the model's context window after truncation). Functions with a null `codeEmbedding` are still included in similarity computation if `descriptionEmbedding` is present. |
| `descriptionEmbedding` | list\<float\> \| null | Embedding vector of the description summary. Null when descriptions are skipped or failed. |
| `createdAt` | string | ISO-8601 timestamp of first insertion. Preserved on re-runs. |
| `updatedAt` | string | ISO-8601 timestamp of most recent change. |
| `lastSeenAt` | string | ISO-8601 timestamp of the most recent scan that included this function. Used to detect deletions. |
| `isDeleted` | boolean | `true` if the function was absent from the most recent scan. |
| `isTest` | boolean | `true` if the function's file path matches any pattern in `pipeline.test_patterns`. Test functions are stored but excluded from similarity computation and report rankings. |
| `codeEmbeddingStatus` | string \| null | Result of the code embedding stage: `"ok"`, `"skipped"` (empty source), `"context_overflow"` (large input, likely exceeded model context), `"timeout"`, or `"error"`. `null` for functions that have not been through an embedding run (e.g. legacy nodes). |
| `codeEmbeddingInputChars` | integer \| null | Length of the raw source code in characters before truncation. Set only on failure. |
| `codeEmbeddingTruncatedChars` | integer \| null | Length of the source code actually sent to the model after truncation. Set only on failure. |
| `descriptionStatus` | string \| null | Result of the description generation stage: `"ok"`, `"skipped"` (run with `--no-descriptions`), `"invalid_json"` (model returned non-JSON after retries), `"timeout"`, or `"error"`. `null` for functions that have not been through a description run. |

### Relationship: `SIMILAR_TO`

Directed edge between two `Function` nodes. Only created when `source.id < target.id` to avoid duplicate pairs.

| Property | Type | Description |
|---|---|---|
| `codeSimilarity` | float | Cosine similarity between the two `codeEmbedding` vectors. |
| `descriptionSimilarity` | float | Cosine similarity between the two `descriptionEmbedding` vectors. `0.0` when descriptions are absent. |
| `combinedSimilarity` | float | Weighted combination: `code_weight × codeSimilarity + description_weight × descriptionSimilarity` when both functions have code embeddings. Falls back to `codeSimilarity` when description embeddings are absent. Falls back to `descriptionSimilarity` alone (unweighted) when at least one function has no code embedding. |
| `createdAt` | string | ISO-8601 timestamp of first creation. Preserved on re-runs via `ON CREATE SET`. |
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

`--report` and `--report-only` create a timestamped directory under `run_reports/` containing two files:

- `report.md` — the full human-readable markdown report
- `report.json` — machine-readable export of all stats, clusters, failures, and flags

`run_reports/` is gitignored. Each run gets its own directory (`run_reports/<timestamp>/`) so previous reports are never overwritten.

The report is fully deterministic — no LLM reasoning is involved. It contains ten sections in order:

| # | Section | Contents |
|---|---|---|
| 1 | **Metadata** | Repo name, timestamp, Neo4j database, pipeline version, embedding model |
| 2 | **Embedding Integrity** | Per-status counts for code embedding and description stages; table of failed functions with stage and error type |
| 3 | **Graph Overview** | Function count, edge count, edge density, isolated ratio, intra-file vs inter-file edge split, language breakdown; LOC-filtered function count (when pipeline ran with a non-zero threshold) |
| 4 | **Similarity Distribution** | Edge counts bucketed by `combinedSimilarity`: > 0.95 / 0.90–0.95 / 0.80–0.90 / ≤ 0.80 |
| 5 | **Top N Most Similar Pairs** | Near-duplicate or shared-logic candidates, sorted by score |
| 6 | **Top N Most Connected Functions** | Functions with the highest edge degree — likely utility or pattern code |
| 7 | **Top N Files by Edge Count** | Per-file edge count with inter-file ratio column |
| 8 | **Duplication Clusters** | Connected components of `SIMILAR_TO` edges at score ≥ `CLUSTER_THRESHOLD` (default 0.92), computed in Python via BFS. Columns: cluster ID, size, max/avg score, files involved, representative function |
| 9 | **Heuristic Flags** | Rule-based diagnostics: `HIGH_DUPLICATION_CLUSTER`, `CROSS_FILE_DUPLICATION`, `ARCHITECTURE_COUPLING`, `TEST_POLLUTION` (only when tests are included) |
| 10 | **Machine-Readable Export** | Fenced JSON block with all stats, embedding counts, cluster list, failures, and top pairs for downstream tooling |

### Thresholds

All report thresholds are configured under `pipeline.reporter` in `config.json`. See `docs/CONFIG.md` for the full field reference.

| Config key | Default | Description |
|---|---|---|
| `cluster_threshold` | `0.92` | Minimum `combinedSimilarity` for an edge to be included in cluster computation |
| `arch_coupling_threshold` | `0.60` | Inter-file edge ratio above which `ARCHITECTURE_COUPLING` is raised (requires ≥ 5 total edges) |
| `test_pollution_threshold` | `5` | Minimum cross-boundary edges (test ↔ production) to raise `TEST_POLLUTION` |
| `timezone` | `"UTC"` | IANA timezone for all report timestamps — set to your local zone (e.g. `"Europe/Stockholm"`) so the `Generated` header and report folder name match your clock |

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
  (config loader moved to src/core/pipeline_config.py)
  scanner.py        — repo file walker with ignore-path pruning
  extractor.py      — tree-sitter AST traversal, emits FunctionRecord per function
  embedder.py       — EmbeddingService: code and description embedding via OllamaClient
  describer.py      — DescriptionService: LLM JSON description generation via OllamaClient
  similarity.py     — Neo4j vector-index query per function, top-N neighbour merging, SimilarityEdge list
  neo4j_store.py    — Neo4jStore: async driver, MERGE upserts, UNWIND batching
  pipeline.py       — EmbeddingPipeline: orchestrates all twelve stages
  reporter.py       — post-run markdown report generator

run_pipeline.py     — CLI entry point
```
