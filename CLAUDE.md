# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is the **core engine** of RepoSwarm: a Temporal-based worker that clones repositories, runs a versioned pipeline of Claude prompts against each one, and commits the resulting `<repo>.arch.md` files to a central "architecture hub" git repo. The CLI, REST API, and web UI live in separate repos (`reposwarm-cli`, `reposwarm-api`, `reposwarm-ui`) — this repo owns workflows, activities, prompts, and storage.

## Commands

Prefer `mise` tasks over ad-hoc shell commands — `mise.toml` is the canonical task registry and each task carries a "Use when:" comment. Run `mise tasks` to list them. Note that `mise.toml` references a few scripts/files that no longer exist (`scripts/full-docker.sh`, `test_dynamodb_local.py`, `test_health_check.py`, `test_workflow_cache_simple.py`), so `investigate-production-docker`, `test-dynamodb*`, `test-health-check`, and `test-workflow-cache` are currently broken.

```bash
mise dev-dependencies       # uv sync
mise get-started            # interactive wizard → writes .env.local
mise verify-config          # validate env + repo access before running anything

mise dev-server             # temporal server start-dev (needed by everything below)
mise dev-worker             # run the Temporal worker (cd src && python -m investigate_worker)
mise dev-client             # trigger InvestigateReposWorkflow with chunk-size 2
mise kill                   # stop all Temporal servers/workers

mise investigate-one [REPO_NAME_OR_URL] [force] [model M] [max-tokens N] [type T] [dry-run]
mise investigate-all [force] [chunk-size N] [sleep-hours N] [dry-run]
mise monitor-workflow <workflow-id>   # query workflow progress
mise cleanup-temp                     # wipe ./temp
```

There is no linter configured. Type checking is pyright in `basic` mode (`pyrightconfig.json`, covers `src`, `tests`, `scripts`).

### Tests

`pytest.ini` sets `testpaths = tests/unit` and `norecursedirs` includes `src`, so a bare `pytest` only runs unit tests. Integration tests must be named explicitly.

```bash
mise test-units          # tests/unit
mise test-integration    # tests/integration, -m "not slow"
mise test-all            # both
```

Development tasks and Docker use Python 3.12; CI tests Python 3.12 and 3.13. Use Python 3.12 to match the development environment:

```bash
uv run --python 3.12 python -m pytest tests/unit/test_config.py -q
uv run --python 3.12 python -m pytest tests/unit/test_config.py::TestArchHubURLConstruction::test_get_arch_hub_repo_url_with_org_url -q
```

Tests add `src` to `sys.path` with `append` or `insert`; follow the nearby test's setup rather than relying on package installation. Unit tests mock `temporalio` at import time where needed (see `tests/unit/test_worker_identity.py`) — do not assume the worker module is importable without it.

## Architecture

### Two workflows, one task queue

The default task queue is `investigate-task-queue`. Worker/client configuration reads `TEMPORAL_TASK_QUEUE`, while the parent workflow currently hardcodes its child-workflow queue to the default. Workers are registered in `src/investigate_worker.py` (the real entry point; `src/worker.py` is an env-validation variant).

- **`InvestigateReposWorkflow`** (`src/workflows/investigate_repos_workflow.py`) — the long-running parent. Refreshes `prompts/repos.json` from the configured git provider, then starts `InvestigateSingleRepoWorkflow` child workflows in **chunks** (`chunk_size`, default 8), awaiting each chunk before starting the next. After the cycle it sleeps `sleep_hours` (default 6) and calls `continue_as_new`, so `force` only applies on `iteration_count == 0`.
- **`InvestigateSingleRepoWorkflow`** (`src/workflows/investigate_single_repo_workflow.py`) — the actual 8-step pipeline, exposed as `get_progress`/`get_status` Temporal queries. Order matters and is subtle: prompts config is loaded **before** the cache check (step 1.5) because prompt versions are an input to the cache decision.

Pipeline: health check → clone → load prompts config → cache check (early-return "skipped") → structure analysis → read/cache dependencies → per-prompt Claude calls → write arch file → push to arch hub → save metadata to DynamoDB → cleanup temp dir.

Ordering constraint: metadata is saved to DynamoDB **after the hub-save step**. A failed hub save raises before metadata is written, so the repo is not marked as investigated and can be retried next cycle. A skipped hub save or successful local-folder save still allows metadata to be recorded. Preserve this ordering.

### Workflow sandbox discipline

Temporal's workflow sandbox forbids I/O and most imports at workflow scope. Consequences you must respect:

- All file/network/AWS work lives in `@activity.defn` functions in `src/activities/`, which do their heavy imports **inside the function body** (`from investigator.core... import ...`) plus a `sys.path.append`. Match this style when adding activities.
- `src/workflow_config.py` is a dependency-free duplicate of validation logic from `src/investigator/core/config.py`, existing solely so workflows can validate inputs. `Config` (investigator) is what actually drives Claude calls; `WorkflowConfig` is not. The two `VALID_CLAUDE_MODELS` lists have drifted — update both when changing model support.

### Prompts: inheritance + versioning

`prompts/base_prompts.json` defines the 17 shared analysis steps (all files under `prompts/shared/`). Each type directory (`backend/`, `frontend/`, `mobile/`, `libraries/`, `infra-as-code/`, `generic/`) has a `prompts.json` that either `extends` the base and appends `additional_prompts`, or stands alone. `FileManager.read_prompts_config` implements the merge; `prompts/shared/*` files are referenced with `../` paths and resolved relative to the type directory.

Repo type is **not** auto-detected at runtime — `RepositoryTypeDetector` just maps the `type` field from `repos.json` to a directory, falling back to `generic`. (`prompts/prompt_selector.json` and `prompts/DETECTION.md` describe a scoring-based detector that the current code path does not use.)

**Every prompt `.md` must start with `version=N` on line 1.** `AnalysisResultsCollector.extract_prompt_version` raises if it's missing, `ClaudeAnalyzer.clean_prompt` strips it before sending, and the version is baked into cache keys. Bumping a version is how you invalidate cached analysis for that step. Prompts substitute `{repo_structure}` and `{previous_context}`.

A step may declare `context: [{"type": "step", "val": "hl_overview"}]`; the workflow threads that prior step's result reference key forward so its output becomes `{previous_context}`. `AnalysisResultsCollector` also hard-fails if the `monitoring` section is missing from combined results — a deliberate tripwire for silently dropped sections, and `EXPECTED_BASE_PROMPT_COUNT` in `src/investigator/core/constants.py` must be kept in sync with `base_prompts.json`.

### Two-level caching

1. **Repo level** — `InvestigationCache.check_needs_investigation` compares the latest commit SHA, branch, and the full prompt-version map against the last DynamoDB investigation record. Any change ⇒ re-investigate.
2. **Prompt level** — inside `analyze_with_claude_context`, each step is keyed by `{repo}_{step}_{commit_sha}_v{version}` (`src/utils/storage_keys.py`). A hit skips the Claude call entirely. `config_overrides.force_section` bypasses it for one step; the workflow sets `force_section = "__all__"` when `force` is passed.

`src/utils/storage_keys.py` is the single source of truth for key formats — DynamoDB uses `to_storage_key()`, file storage uses `to_file_safe_key()`. Never hand-build these strings.

### Pluggable storage

`src/utils/prompt_context.py` is a factory over `PromptContextBase`: DynamoDB (`prompt_context_dynamodb.py`) or local files under `./temp/prompt_context_storage/` (`prompt_context_file.py`). Selection is `PROMPT_CONTEXT_STORAGE` = `file` | `dynamodb` | `auto` (auto sniffs `DYNAMODB_*`, ECS metadata, AWS creds, `TEMPORAL_WORKER`). Large prompt payloads are chunked across DynamoDB items; items carry TTLs.

Claude-analysis activities use storage reference keys to retrieve context. Some surrounding activities still pass full prompt, structure, dependency, and result content through Temporal payloads. Prefer references when adding large payloads; workflow history size is a real constraint here (hence `continue_as_new`).

### Multi-provider seams

- **Git** (`src/investigator/core/git_manager.py`): GitHub, CodeCommit, GitLab, Bitbucket, Azure DevOps. Auth uses a temporary **git credential-store helper file** that is written, used, and deleted — credentials are deliberately not embedded in remote URLs (see recent commits). `_sanitize_url_for_logging` / `_sanitize_error_message` keep secrets out of logs; keep new code paths behind them. Provider selection for repo discovery is via `*_ENABLED` env flags (`CODECOMMIT_ENABLED`, `GITLAB_ENABLED`, `BITBUCKET_ENABLED`, `AZURE_DEVOPS_ENABLED`), falling back to GitHub.
- **LLM** (`src/investigator/core/claude_analyzer.py`): standard Anthropic API vs Bedrock, chosen by `CLAUDE_PROVIDER=bedrock` or `CLAUDE_CODE_USE_BEDROCK=1`. `BEDROCK_MODEL_MAPPING` translates plain model names to Bedrock IDs; `us.anthropic.*` / `anthropic.*` IDs pass through validation untouched.
- **Arch hub output**: `ARCH_HUB_MODE=git` (clone, write, commit, push) or `local` (write to `ARCH_HUB_LOCAL_PATH`). If `ARCH_HUB_BASE_URL` is still the `https://github.com/your-org` placeholder, the save is **skipped**, not failed.

### Models

`src/models/` holds all Pydantic models (investigation, cache, activities, workflows) and both client and worker use `pydantic_data_converter`. Activity signatures take/return these models rather than loose dicts — though several older activities still return plain `dict` and the workflow converts at the boundary (e.g. `CloneRepositoryResult(**clone_result)`).

## Config

Env is loaded from `.env.local` then `.env` (mise `[env] _.file`), with `PYTHONPATH={{cwd}}`. `env.example` / `env.local.example` are the templates. Local development typically sets `LOCAL_TESTING=true`, `SKIP_DYNAMODB_CHECK=true`, `PROMPT_CONTEXT_STORAGE=file` — the first two let the health-check activity pass without DynamoDB.

`mise dev-worker` does `cd src` first: modules import each other as top-level packages (`from activities...`, `from workflows...`), so `src` must be on the path. The Dockerfile sets `PYTHONPATH=/app/src` and `WORKDIR /app/src` for the same reason.

## Conventions

From `.cursor/rules/`:

- Be pragmatic and neutral. When bugs are present, describe them plainly ("the failure seems to be…"), not optimistically. Avoid exclamation points and cheerleading.
- Analyze thoroughly before proposing fixes; give concrete diagnostic steps before code changes.
- If you find yourself repeating a shell command for debugging, consider adding it as a `mise.toml` task (ask first).

CI (`.github/workflows/ci.yml`) runs unit tests on Python 3.12 and 3.13, then integration tests, then builds and pushes a multi-arch `ghcr.io/reposwarm/worker` image on pushes to `main` that touch non-docs files.

`.gitallowed` whitelists mock credential strings used in adapter unit tests — new fake credentials in tests may need adding there to pass secret scanning.
