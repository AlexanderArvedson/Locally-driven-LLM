# Project use-cases

## Tested use-cases so far

- Code refactoring/update
- Documentation
- Incremental change detection

## Results

### Code refactoring

Current results are iffy, at one time it initially changed a lot more than was instructed in the task itself, where instead of removing the type hint from a single specified function, it removed all of the ones from the entire file. 

---

No — the function removed in the last commit (append_line_many) is still used.

It is called in macro_activation_handler.py:1100.
It is called in data_processing_task.py:70.

With the command to remove dead code, and without a specific target file, it broke a use case by removing a function used in other places.

required specific name to modify, with correct syntax. otherwise it did not know what to do.

### Documentation

Single test done, decent results so far. It seems to have successfully added docstrings to all the functions in the file, without destroying anything.

For both of the current test cases, the file used was `apps\desktop\python_integration\modules\config_handler\dto_map.py` from the modukey monorepo

---

## Embedding similarity — description weight experiment

### Setup

Four pipeline runs were performed against a Python subfolder of the modukey monorepo (321 functions, ~40 min per run). Each run used the same extracted functions and pre-computed embeddings; only the similarity weighting was varied. The similarity threshold was 0.90 throughout.

| Run | `code_weight` | `description_weight` |
|---|---|---|
| Code-only | 1.0 | 0.0 |
| Hybrid 7/3 | 0.7 | 0.3 |
| Hybrid 5/5 | 0.5 | 0.5 |
| Desc-only | 0.0 | 1.0 |

### Results

| Metric | Code-only | Hybrid 7/3 | Hybrid 5/5 | Desc-only |
|---|---|---|---|---|
| Similarity edges | 374 | **508** | 304 | 271 |
| Near-identical (> 0.95) | 20 | **39** | 13 | 14 |
| Isolated functions | 119 | **105** | 131 | 140 |
| Duplication clusters | 33 | **38** | 34 | 30 |
| Inter-file edge ratio | 31% | 28% | 36% | **40%** |

### Conclusions

**Code embeddings are the primary signal.** Code-only outperforms desc-only on every volume metric. Raw source structure is more discriminative than LLM-summarised intent for detecting similar functions.

**The weight–performance relationship is non-linear.** The ordering is: desc-only (271) < 5/5 (304) < code-only (374) < 7/3 (508). Equal weighting performs worse than no descriptions at all. At 5/5, a mediocre description (e.g. sim 0.85) drags a structurally strong pair (code sim 0.95) to a combined score of 0.90 — right at or below threshold. The 7/3 split bounds this penalty: the same pair scores 0.91, kept. The asymmetric weight protects structural pairs while still allowing descriptions to lift genuinely borderline ones.

**Descriptions find qualitatively different things.** The gamepad driver duplication cluster expanded from 7 to 14 functions (absorbing keyboard, mouse, and HID bridge drivers) when descriptions were included — a real architectural pattern that code similarity alone did not fully connect. Description-only also surfaced a cross-file `__init__` cluster spanning 8 service files that code-only missed entirely. These are semantic relationships invisible to structural similarity.

**The optimal weight is threshold-dependent.** At threshold 0.90, 7/3 is the clear optimum. At a lower threshold more description-driven pairs would qualify naturally and a higher description weight could become viable. The two values should be tuned together, not independently.

**Descriptions degrade gracefully on failure.** Functions that fail description generation still participate in the graph via code-only similarity (the fallback path uses raw `code_sim` with no weighting applied). No description failure can prevent a strongly similar structural pair from forming an edge.

**Cost vs. benefit.** The description stage (LLM chat completions, concurrency 2) accounts for the majority of the ~40-minute run time on this subfolder, and up to 24+ hours on a full repository. At 7/3 weighting, descriptions add 36% more edges and surface cross-file architectural patterns that code alone misses. For a one-time analysis the cost is justified. For frequent automated runs on large repos, the marginal gain should be weighed against runtime.

---

## Describer model size — 14B vs 7B comparison

### Setup

Two pipeline runs against `kreation-core/src` from the kreation monorepo (64 TypeScript functions). Both runs used identical config except for the describer model. `num_ctx` was 12288 for both runs. A third run with 7B at `num_ctx: 16384` was added to test whether the additional context resolves the `upload` failure.

| Run | Model | `num_ctx` | Duration |
|---|---|---|---|
| Run 1 | `qwen2.5-coder:14b` | 12288 | 1883.8 s (~31 min) |
| Run 2 | `qwen2.5-coder:7b` | 12288 | — |
| Run 3 | `qwen2.5-coder:7b` | 16384 | — |

### Results

| Metric | 14B (12288) | 7B (12288) | 7B (16384) |
|---|---|---|---|
| `ok` | 63 / 64 | 62 / 64 | 62 / 64 |
| `invalid_json` | 1 | 2 | 2 |
| Failed functions | `parseMixedContent` | `parseMixedContent`, `upload` | `parseMixedContent`, `upload` |

### Quality observations

**~95% of functions: identical quality across all three runs.** Simple functions (constructors, pure utilities, logger methods, short service helpers) produced descriptions of equivalent depth and accuracy. Conciseness was marginally better in 7B on simple cases.

**`upload` failure is a 7B capability limit, not a context window issue.** The function failed with `invalid_json` in both Run 2 (12288) and Run 3 (16384). Increasing `num_ctx` made no difference. `upload` is the most complex function in the codebase (~50 lines, 5 parameters, DynamoDB + S3 interaction, conditional deduplication logic). 14B produced a complete description for it. This failure is inherent to 7B on highly complex functions and cannot be addressed by tuning context size.

**`parseMixedContent` fails consistently across all models.** Failed in 14B (Run 1) and both 7B runs. Likely a genuinely difficult function (mixed content parsing) that pushes the structured JSON output schema regardless of model size.

**Persistent 7B hallucinations (2, confirmed across both 7B runs):**
- `verify` in `service/jwtHelper.ts` — described return type as `Promise<decoded payload>`. The function is synchronous; `jwt.verify` is not async. Present in Run 2 and Run 3.
- `normalizeEntityTodoBoardStatus` — described a throw (`InvalidInputError`) for invalid input. The function defaults to `'open'`; it does not throw. Present in Run 2 and Run 3.

**Non-deterministic 7B hallucinations (resolved in Run 3):**
- `importMusicMetadata` — Run 2 described a side effect of "loads a JavaScript module using eval-like functionality". Run 3 correctly says "Asynchronously loads the 'music-metadata' module." No eval involved.
- `entityTodoBoardStatusImpliesUserEngaged` — Run 2 described the boolean return as "true if not engaged, false if engaged" (inverted). Run 3 got it correct: "true if engaged, false otherwise."

**Places 7B was equal or better than 14B:**
- `getFileExtemsion` — 7B explicitly enumerated the valid extensions; more informative than 14B's generic phrasing.
- `addFileIndex`, `fileExistsWithClient` — 7B's structured sideEffects/errors formatting was slightly cleaner.
- `getSecret` in `credentials.ts` — Run 3 correctly captured the in-memory caching behaviour that Run 2 missed.

### Conclusions

**7B is viable for this codebase.** The failure rate is low (2/64 vs 1/64) and hallucinations are isolated rather than systemic.

**`upload` failing is a hard 7B limit.** The `num_ctx` bump to 16384 did not help. The function requires model reasoning depth beyond what 7B can reliably sustain for structured JSON output. Workaround options: accept the missing description, manually write it, or use 14B as a targeted fallback for functions that fail 7B.

**Two hallucinations are stable and should be treated as known defects.** `verify` (false async annotation) and `normalizeEntityTodoBoardStatus` (false throw) recurred across both 7B runs. They are type/contract mistakes, not behavioural logic mistakes — risky if the graph is queried for interface contracts, acceptable if queried for behavioural intent.

**Speed tradeoff.** 7B runs ~1.5–2× faster than 14B. On a 64-function repo the absolute saving is modest. On a 500-function repo it becomes the difference between a ~4-hour and a ~2-hour pipeline run. For teams running the pipeline frequently on large repos, 7B is the right default.

**Recommendation:** Use `qwen2.5-coder:7b` with `num_ctx: 16384` as the default describer. Switch to 14B when: (a) the codebase has a high proportion of large, complex functions (>50 LOC), or (b) description accuracy for interface contracts is load-bearing for downstream tooling.

---

## Incremental change detection

### Setup

Two consecutive `--no-description` runs against `kreation-core/src` (64 functions). A single function was modified between runs. Both runs used the existing Neo4j graph — no clean between them.

### Results

| Run | Changed | Unchanged | Duration |
|---|---|---|---|
| Run 1 (baseline, post-clean) | 64 | 0 | 3.0 s |
| Run 2 (one function modified) | 1 | 63 | 2.6 s |

### Conclusions

**Change detection works correctly.** The pipeline identified exactly the one modified function and processed only that — 63 unchanged functions were skipped entirely. The graph was updated and similarity edges recomputed in under 3 seconds.

**Incremental runs are effectively free.** At sub-3-second turnaround for a small delta, the pipeline can be run on every commit without any meaningful overhead. The description stage (when enabled) will similarly only run on changed functions, making 7B vs 14B model choice largely irrelevant for day-to-day incremental use — the cost only materialises on the initial full run or after a bulk refactor.