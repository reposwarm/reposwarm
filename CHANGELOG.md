# Changelog

## 2026-03-08 — Sequential investigation mode (worker concurrency limits)

### Problem

Running `reposwarm investigate --all` on resource-constrained machines (16GB RAM) caused Temporal deadlock errors (`TMPRL1101`). The worker had no concurrency limits, so all repos cloned and analyzed in parallel, saturating I/O/CPU and blocking the Temporal event loop for >2 seconds.

### Solution

The worker now reads `REPOSWARM_PARALLEL` from its environment to limit concurrent activities. This env var is managed automatically by the CLI's `--parallel` flag — no manual configuration needed.

```
reposwarm investigate --all --parallel=1     # CLI sets REPOSWARM_PARALLEL=1, restarts worker, runs sequentially
```

### Changes

- `src/investigate_worker.py` — Reads `REPOSWARM_PARALLEL` env var. When set to a positive integer, passes `max_concurrent_activities` and `max_concurrent_workflow_task_polls` to the Temporal `Worker()` constructor. Default (unset/0) = unlimited, preserving cloud behaviour.
- `.env.example` — Documented `REPOSWARM_PARALLEL` with note that it is managed by the CLI.

### Related

See `lac-reposwarm-cli` CHANGELOG for the CLI-side changes (`--parallel` flag, sequential dispatch, worker restart logic).
