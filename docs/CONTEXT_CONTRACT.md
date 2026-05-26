# Repository Context Contract (retrieval → coder)

Last updated: 2026-05-26

This document describes the authoritative, versioned contract used to pass
repository-level context from the retrieval/context-builder nodes into the
coder node prompt. The canonical implementation lives at
`src/repository/context_contract.py` and contains the serializer,
validator, and prompt renderer used across nodes and tests.

## Purpose

- Provide a deterministic, bounded, and versioned payload representing the
  repository context relevant to a target file and a task.
- Make prompt rendering predictable and easy to snapshot/test.
- Keep repository-relative paths to avoid ephemeral tmpdir differences.

## Contract version

- The contract currently exposes `CONTEXT_VERSION = 1`.
- Any incompatible change must increment the version and update the
  serializer/validator and tests accordingly.

## Payload shape

The payload is a mapping with the following required fields (names are
literal):

- `context_version` (int): contract version number.
- `primary_file` (str|null): normalized path to the primary/target file.
- `selected_files` (list[str]): ordered list of files selected by retrieval.
- `related_files` (list[str]): additional related files (ordered).
- `related_symbols` (dict[str, list[str]]): mapping from file -> list of
  symbol names present in that file.
- `dependency_summary` (list[object]): list of dependency edges where each
  item contains `from_path`, `to_path`, and optional `import_text`.
- `total_symbols` (int): total count of extracted symbols in the context
  package (for informational ordering / diagnostics).

All paths in the payload are normalized relative to the repository root when
`repo_path` is available. This is critical to keep serialized payloads stable
across runs and environments.

## Determinism rules

- Lists are deduplicated while preserving the first seen order.
- If `primary_file` is present and is also in `selected_files`/`related_files`,
  it is forced to be the first element in those lists (target-first rule).
- `dependency_summary` is sorted by `(from_path, to_path, import_text or "")`.
- `related_symbols` keys are traversed in sorted order when rendering to a
  prompt to ensure stable ordering.

## Validation

The validator enforces:

- Presence of all required fields.
- `context_version` must equal the expected `CONTEXT_VERSION`.
- `selected_files` must be a list.
- `primary_file` (if present) must be the first entry in `selected_files`.

The validator returns a `(bool, str)` tuple: a success flag and a short
reason string used by tests and diagnostics.

## Prompt rendering

The canonical prompt renderer renders a compact, human-readable section
prefixed with `[REPOSITORY CONTEXT]` and the following sub-structure:

- `- context_version: <n>`
- `- selected_files:` followed by an enumerated list (`1. path`).
- `- related_symbols:` with sorted file keys and comma-separated symbol
  lists per file (`- file.py: sym1, sym2`).
- `- total_symbols: <n>`

If the payload is missing or invalid the renderer returns `- none` or
`- invalid` respectively after the `[REPOSITORY CONTEXT]` header. The
coder node places this rendered block into the user prompt; tests assert on
the exact formatting to detect accidental prompt drift.

## Where it's used

- `src/graph/nodes/nodes.py` — `context_builder_node` builds the payload via
  `build_repository_context_payload(...)` and stores it in graph state.
- `src/graph/nodes/nodes.py` — `coder_node` calls
  `format_repository_context_for_prompt(...)` to get a stable prompt section.
- Tests in `tests/` import the constants and validator from
  `src/repository/context_contract.py` to assert correctness and determinism.

## Example payload

```
{
  "context_version": 1,
  "primary_file": "a.py",
  "selected_files": ["a.py", "b.py", "tests/test_a.py"],
  "related_files": ["a.py", "b.py"],
  "related_symbols": {"a.py": ["x"], "b.py": ["helper"]},
  "dependency_summary": [
    {"from_path": "a.py", "to_path": "b.py", "import_text": "b"}
  ],
  "total_symbols": 3
}
```

## Changing the contract

- When extending the contract, add new optional keys rather than changing
  existing required keys if possible.
- For breaking changes increment `CONTEXT_VERSION` and update the validator
  and test snapshots.

## Tests and diagnostics

- Tests exercise both serializer and formatter to ensure the exact markdown
  that the LLM sees is stable for golden snapshot testing.
- Prefer unit tests for stable invariants (ordering, normalization) and
  integration tests covering end-to-end graph runs to validate the
  stored payload in `GraphState` and runtime JSONL logs.
