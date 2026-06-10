# Project use-cases

## Tested use-cases so far

- Code refactoring/update
- Documentation

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