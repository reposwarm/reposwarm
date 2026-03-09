# Changelog

## 2026-03-08 — Fix 4 investigation failures (rate limits, prompt overflow, gRPC payload, data_content bug)

### Problems

1. **Rate limiting (429)** — camel-spring-boot-examples and argo-cd hit the Anthropic API rate limit (30K input tokens/min). The activity only retried 3 times with short backoff (5s→10s→20s), insufficient for sustained rate limits.
2. **Prompt too long (400)** — keycloak's `module_deep_dive` step assembled 209,832 tokens, exceeding the 200K context window. No token validation existed before the API call.
3. **gRPC payload too large** — quarkus has 2,215 dependency files totalling 13.4MB. `read_dependencies_activity` returned full file contents inline, exceeding Temporal's 4MB gRPC message limit.
4. **`data_content` parameter mismatch** — `cache_dependencies_activity` called `save_temporary_analysis_data(data_content=...)` but the method expects `prompt_content` and `repo_structure` parameters. TypeError at runtime.

### Changes

- **`src/utils/dynamodb_client.py`** — Added `save_generic_data()` and `_save_chunked_generic_data()` methods for storing arbitrary JSON-serializable data with compression/chunking support. Updated `get_temporary_analysis_data()` to handle the `is_generic` flag on retrieval.
- **`src/activities/investigation_cache.py`** — Fixed `save_dependencies()` to call `save_generic_data()` instead of the broken `save_temporary_analysis_data(data_content=...)`.
- **`src/activities/investigate_activities.py`** — `read_dependencies_activity` now saves raw dependencies to DynamoDB inside the activity and returns only a reference key through gRPC. Added `repo_name` parameter for storage key generation. Added `formatted_content` truncation to 500KB to prevent gRPC message size limit on repos with thousands of dependency files (e.g. quarkus: 2,215 files / 6.5MB formatted).
- **`src/workflows/investigate_single_repo_workflow.py`** — Simplified `_read_and_cache_dependencies()` (removed separate `cache_dependencies_activity` call). Increased `analyze_with_claude_context` retry policy to 6 attempts / 15s initial / 2min max. Added optional `INTER_STEP_DELAY_SECONDS` env var for inter-step throttling. Moved `os.getenv` call to module level to avoid Temporal sandbox `RestrictedWorkflowAccessError`.
- **`src/investigator/core/config.py`** — Added `MAX_INPUT_TOKENS` (180K) and `CHARS_PER_TOKEN_ESTIMATE` (3.5) configuration constants.
- **`src/investigator/core/claude_analyzer.py`** — Added `_estimate_tokens()` and `_truncate_to_fit()` methods for prompt truncation. Fixed truncation flow so template truncation (last resort) is always reachable — previously an early return when `previous_context` existed prevented template truncation from ever executing (caused keycloak 206K token failures). Added rate-limit-aware error handling: catches `RateLimitError`, extracts `retry-after` header, sleeps with logging before re-raising for Temporal retry.

---

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
