# Runtime Lifecycle and Cancellation

Last updated: 2026-05-27

This document describes the deterministic execution lifecycle used by the
runtime scheduler, registry, queue, and executor.

## Purpose

The runtime layer coordinates repository workflows without exposing LangGraph
internals to callers. The registry is the system of record, the queue is a
temporary dispatch buffer for mutating runs, and the executor owns repository
state validation and cleanup.

## Components

- `src/runtime/models.py` defines the execution contracts and lifecycle
  enums.
- `src/runtime/registry.py` persists run state in SQLite.
- `src/runtime/queue.py` keeps queued mutation runs in memory.
- `src/runtime/executor.py` performs the actual workflow execution.
- `src/runtime/scheduler.py` coordinates submission, dispatch, and cleanup.

## Run States

The registry stores each run in one of these states:

- `pending`
- `queued`
- `running`
- `completed`
- `failed`
- `cancelled`

The expected flow for a normal active run is:

1. `pending` when the request is created.
2. `queued` when the request is placed into the mutation queue.
3. `running` when the scheduler dispatches the request.
4. `completed` or `failed` after the executor returns.

Passive runs skip the queue and go directly from `pending` to `running`.

## Registry Behavior

The registry is the durable record of run lifecycle state. It stores:

- the workflow mode and capability
- the repository path and repository revision
- timestamps for queued, started, and completed transitions
- the final status and error text, if any
- the serialized request payload and execution metadata

The registry is intentionally SQLite-backed so status transitions remain
deterministic and easy to inspect during manual runs and tests.

## Cancellation Behavior

Cancellation is cooperative.

### Queued runs

If a run is still `queued`, the scheduler removes it from the in-memory queue
and marks the registry entry as `cancelled`.

### Running runs

If a run is already `running`, the scheduler marks the registry entry as
`cancelled` and the executor observes the cancellation token at safe
checkpoints:

- before workflow start
- after each graph node wrapper returns

The runtime does not hard-kill threads, terminate processes, or forcefully
cancel coroutines.

### Completed runs

If a run has already reached a terminal state (`completed`, `failed`, or
`cancelled`), cancellation is a no-op and returns `False`.

## Manual Testing

The scheduler has a one-shot smoke entry point:

```bash
uv run python -m src.runtime.scheduler
```

That command only executes a single scheduler tick. To test the full
submission-to-execution path, submit a run from Python, then call
`dispatch_next_mutation()`.

For local model testing, the graph smoke script uses the Ollama client
directly:

```bash
uv run python -m scripts.test_graph
```

## Notes

- The mutation queue is intentionally in-memory for the current MVP.
- A cancelled run may still finish its current safe checkpoint before the
  executor observes the cancellation and returns a cancelled result.
- The registry should remain the source of truth for lifecycle state, even if
  the queue entry is removed.