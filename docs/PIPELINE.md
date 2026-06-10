# Function Embedding and Similarity Pipeline

The pipeline subsystem scans a source code repository, extracts every function and method as standalone text, generates vector embeddings and LLM descriptions for each one, stores the results in Neo4j, and builds a weighted similarity graph between related functions.

It is a standalone subsystem under `src/pipeline/` and shares no code with the LangGraph workflow under `src/graph/`. The only shared dependency is `src/core/ollama_client.py`.

---

## How it works

Before the numbered stages run, the pipeline performs a **pre-flight repo sync**:

- If `local_path` (the configured repo directory) does not exist, the pipeline clones it from `url` using the credentials in `credentials.git`.
- If `local_path` already exists, the pipeline checks out `base_branch` and runs `git pull` so the local clone is up to date before extraction begins.
- If the working tree has uncommitted changes, the checkout/pull is skipped with a warning (guards against discarding in-progress work that should not normally be present in a pipeline-target repo).
- The sync step is skipped entirely when `url` is not configured (useful for local-only repos or test configurations).

The sync always runs against the canonical `local_path` from config, even when `--path` is used to target a subfolder for quick testing.

The pipeline then runs thirteen sequential stages:

1. **ensure_schema** — creates Neo4j constraints, property indexes, and vector indexes if they do not already exist.
2. **extract** — walks the repository with tree-sitter, extracting every function and method as a `FunctionRecord` with source text, line numbers, language, and class membership. When `ignore_anonymous_callbacks` is `true` (default), functions that were given a synthetic location-based name by the extractor — such as `useEffect$0@L87` or `map@L42` — are skipped. These are unnamed inline callbacks that produce structural-similarity noise in the graph because all instances of the same hook or iterator pattern appear identical to the embedding model.
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
# Full run — embeddings, descriptions, similarity graph, and report
uv run run_pipeline.py

# Skip LLM descriptions — much faster, code-embedding similarity only
uv run run_pipeline.py --no-descriptions

# Target a specific subfolder instead of the whole repo
uv run run_pipeline.py --path /path/to/monorepo/apps/backend --no-descriptions

# Validate extraction counts without touching Neo4j or Ollama (no report)
uv run run_pipeline.py --dry-run

# Skip the report after the pipeline
uv run run_pipeline.py --no-descriptions --no-report

# Generate a report from the current Neo4j graph without re-running the pipeline
uv run run_pipeline.py --report-only

# Use a specific repository entry from config.json
uv run run_pipeline.py --repo my-other-repo
```

### Options

| Flag | Description |
|---|---|
| `--config PATH` | Path to `config.json`. Defaults to `./config.json`. |
| `--repo NAME` | Repository name to use from `config.json`. Defaults to the first entry. |
| `--path PATH` | Override `repo_path` from config. Useful for targeting a subfolder. |
| `--dry-run` | Extract functions and query Neo4j for hashes, but skip all Ollama calls, Neo4j writes, and report generation. |
| `--no-descriptions` | Skip LLM description generation and description embeddings. Recommended for first runs on large repositories. |
| `--no-report` | Skip report generation after the pipeline completes. |
| `--report-only` | Skip the pipeline entirely and generate a report from the current Neo4j graph. |

### Running via Slack

The `/pipeline` slash command triggers a pipeline run and posts a Block Kit report to `SLACK_NOTIFY_CHANNEL` on completion. A separate `/report` command generates a report from the current graph without re-running the pipeline.

```
/pipeline
/pipeline --no-descriptions
/pipeline --no-report
/pipeline --dry-run
/pipeline --path /home/alice/projects/myrepo/apps/backend --no-descriptions
/report
```

On completion the bot posts a Block Kit notification to `SLACK_NOTIFY_CHANNEL` if that env var is set. See `docs/guides/slack.md` for setup instructions.

> **Note:** The bot runs inside Docker. For the pipeline to read source files, `REPOS_ROOT` must be set in `.env` to the parent directory of your repos. Paths passed via `--path` must also fall under `REPOS_ROOT`. See `docs/CONFIG.md` for details.

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
| `descriptionStatus` | string \| null | Result of the description generation stage: `"ok"`, `"skipped"` (run with `--no-descriptions`), `"invalid_json"` (response contained no parseable JSON object after stripping code fences and extracting the outermost `{…}` block — tried twice before giving up), `"timeout"`, or `"error"`. `null` for functions that have not been through a description run. |

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

By default, a report is generated automatically after every pipeline run (unless `--no-report` or `--dry-run` is passed). `--report-only` skips the pipeline and generates a report from the current Neo4j graph. Both paths create a timestamped directory under `run_reports/<repo_name>/` containing two files:

- `<repo_name>_report_<timestamp>.md` — the full human-readable markdown report
- `<repo_name>_report_<timestamp>.json` — machine-readable export of all stats, clusters, failures, and flags

For example: `run_reports/my-repo/20260606-142530/my-repo_report_20260606-142530.md`

`run_reports/` is gitignored. Each repository gets its own subdirectory, and within it each run gets its own timestamped directory. Both files carry the repo name prefix and the same timestamp, so reports sort correctly per repo and remain unambiguous when multiple are open at once.

The report is fully deterministic — no LLM reasoning is involved. It contains thirteen sections in order:

| # | Section | Contents |
|---|---|---|
| 1 | **Metadata** | Repo name, timestamp, Neo4j database, pipeline version, embedding model, chat model, describer model, report generation time |
| 2 | **Delta Since Previous Run** | File count, function count, edge count, isolated count, and cluster count compared against the most recent prior `<repo>_report_*.json` in the same repo directory. Omitted on the first run. |
| 3 | **Embedding Integrity** | Per-status counts for code embedding and description stages; table of failed functions with stage and error type |
| 4 | **Graph Overview** | Function count, edge count, edge density, isolated ratio, intra-file vs inter-file edge split, language breakdown, LOC-filtered count; subsection listing each isolated function with its embed status |
| 5 | **Similarity Distribution** | Edge counts bucketed into four ranges defined by `sim_dist_bin_high`, `sim_dist_bin_mid`, and `sim_dist_bin_low` (defaults: 0.95 / 0.90 / 0.80) |
| 6 | **Top N Most Similar Pairs** | Near-duplicate or shared-logic candidates, sorted by score |
| 7 | **Top N Most Connected Functions** | Functions with the highest edge degree; intra-file and inter-file counts shown separately — high intra = local utility, high inter = cross-codebase pattern or duplication |
| 8 | **Top N Files by Edge Count** | Per-file edge count with inter-file ratio column |
| 9 | **Top N Files by Function Count** | Files ranked by number of functions; files above `god_file_threshold` (default 20) are marked and flagged as `GOD_FILE` |
| 10 | **File Cohesion Scores** | Average pairwise embedding similarity of functions within each file, sorted ascending. Low score = semantically unrelated functions = potential SOC violation. Includes the outlier function (lowest avg similarity to its filemates) per file |
| 11 | **Class Cohesion Scores** | Same computation as File Cohesion but grouped by class name. Omitted entirely when the repo has no classes |
| 12 | **Duplication Clusters** | Connected components of `SIMILAR_TO` edges at score ≥ `cluster_threshold` (default 0.92), computed in Python via BFS. Columns: cluster ID, size, max/avg score, files involved, representative function |
| 13 | **Heuristic Flags** | Rule-based diagnostics: `HIGH_DUPLICATION_CLUSTER`, `CROSS_FILE_DUPLICATION`, `ARCHITECTURE_COUPLING`, `TEST_POLLUTION` (only when tests are included), `LOW_COHESION`, `GOD_FILE` |

### Thresholds

All report thresholds are configured under `pipeline.reporter` in `config.json`. See `docs/CONFIG.md` for the full field reference.

| Config key | Default | Description |
|---|---|---|
| `cluster_threshold` | `0.92` | Minimum `combinedSimilarity` for an edge to be included in cluster computation |
| `arch_coupling_threshold` | `0.60` | Inter-file edge ratio above which `ARCHITECTURE_COUPLING` is raised |
| `test_pollution_threshold` | `5` | Minimum cross-boundary edges (test ↔ production) to raise `TEST_POLLUTION` |
| `timezone` | `"UTC"` | IANA timezone for all report timestamps — set to your local zone (e.g. `"Europe/Stockholm"`) |
| `top_n` | `20` | Items shown in each ranked section (Similar Pairs, Connected Functions, Files by Edge Count) |
| `max_embedding_failures` | `200` | Maximum rows in the Embedding Failure Table |
| `high_dup_min_cluster_size` | `3` | Minimum cluster size to raise `HIGH_DUPLICATION_CLUSTER` |
| `high_dup_min_score` | `0.95` | Minimum cluster `max_score` to raise `HIGH_DUPLICATION_CLUSTER` |
| `cohesion_low_threshold` | `0.30` | Files with an average pairwise similarity below this value are flagged `LOW_COHESION` |
| `cohesion_min_functions` | `2` | Minimum number of embeddable functions required to compute a cohesion score for a file or class |
| `max_cohesion_files_listed` | `20` | Maximum rows shown in the File Cohesion and Class Cohesion tables |
| `max_isolated_listed` | `50` | Maximum isolated functions shown in the Isolated Functions subsection |
| `god_file_threshold` | `20` | Files with more functions than this value are flagged `GOD_FILE` |
| `min_coupling_edges` | `5` | Minimum total edges a file must have before `arch_coupling_threshold` is evaluated |
| `max_coupling_files_listed` | `5` | Maximum file paths shown in the `ARCHITECTURE_COUPLING` flag message |
| `sim_dist_bin_high` | `0.95` | Upper boundary of the top similarity bucket |
| `sim_dist_bin_mid` | `0.90` | Middle boundary of the similarity histogram |
| `sim_dist_bin_low` | `0.80` | Lower boundary — edges at or below this fall in the bottom bucket |

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
  contracts.py          — FunctionRecord, SimilarityEdge, PipelineConfig dataclasses
  pipeline.py           — EmbeddingPipeline: orchestrates all twelve stages

  extraction/
    scanner.py          — repo file walker with ignore-path pruning
    treesitter.py       — tree-sitter language setup, AST traversal helpers
    extractor.py        — FunctionExtractor: emits FunctionRecord per function

  embeddings/
    service.py          — EmbeddingService: code and description embedding via OllamaClient

  descriptions/
    prompts.py          — LLM prompt template constant
    service.py          — DescriptionService: LLM JSON description generation via OllamaClient

  graph/
    store.py            — Neo4jStore: async driver, MERGE upserts, UNWIND batching
    similarity.py       — vector-index query per function, top-N neighbour merging, SimilarityEdge list

  reporting/
    queries.py          — Cypher query string constants
    analysis.py         — cluster computation, cosine similarity, cohesion scoring, flag derivation
    export.py           — _build_export: assembles the machine-readable JSON export dict
    markdown/
      __init__.py       — re-exports all render_* names
      overview.py       — render_metadata, render_summary, render_delta
      integrity.py      — render_embedding_integrity
      topology.py       — render_graph_overview, render_similarity_distribution, render_top_pairs,
                          render_most_connected, render_files_by_edge_count, render_files_by_function_count
      quality.py        — render_file_cohesion, render_class_cohesion, render_duplication_clusters,
                          render_heuristic_flags
    reporter.py         — generate_report: post-run markdown report orchestrator

run_pipeline.py         — CLI entry point

src/api/
  pipeline_notifier.py  — PipelineProgressNotifier: posts stage/progress updates to a Slack thread during the pipeline run

src/git/
  branch_manager.py     — SyncResult dataclass, ensure_repo_synced (pre-flight clone/pull), clone_if_missing, create_task_branch, commit_file, push_branch
```
