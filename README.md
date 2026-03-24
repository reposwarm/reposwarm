# 🤖 RepoSwarm

<p align="center">
  <img src="assets/banner-nodes.png" alt="RepoSwarm - Multi-Repo Architecture Discovery" width="100%">
</p>

<p align="center">
  <strong>AI-powered multi-repo architecture discovery platform</strong>
</p>

<p align="center">
  <a href="https://github.com/reposwarm/reposwarm/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://www.youtube.com/watch?v=rOMf9xvpgtc"><img src="https://img.shields.io/badge/Demo-YouTube-red.svg?style=for-the-badge&logo=youtube" alt="YouTube Demo"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#what-is-reposwarm">What Is It</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#ecosystem">Ecosystem</a> •
  <a href="#contributing">Contributing</a>
</p>

> **📦 Previously `loki-bedlam/repo-swarm`. Moved to the [RepoSwarm organization](https://github.com/reposwarm). Old URLs redirect automatically.**

---

## Quick Start

Install the CLI and bootstrap everything in one shot:

```bash
curl -fsSL https://raw.githubusercontent.com/reposwarm/reposwarm-cli/main/install.sh | sh
```

Then:

```bash
reposwarm new --local             # Bootstrap everything: Temporal, API, Worker, UI
reposwarm doctor                  # Full health check
reposwarm repos add my-app --url https://github.com/org/my-app
reposwarm investigate my-app      # Run your first investigation
reposwarm dashboard               # Watch it work
```

That's it. The CLI handles setup, configuration, investigation, diagnostics, and results — all from a single binary.

### Prerequisites

- **Docker must be running** (not just installed) — all services run as containers
- **Git** — for cloning repositories during investigation

### Bedrock Users

If using Amazon Bedrock, the worker needs these env vars (set automatically by the CLI):
- `CLAUDE_CODE_USE_BEDROCK=1`
- `AWS_REGION=us-east-1` (or your region)
- `ANTHROPIC_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0` (or your preferred model)

Auth options: IAM role (recommended), access keys, AWS profile, or Bedrock API keys.
See [CLI docs](https://github.com/reposwarm/reposwarm-cli#-configure-llm-provider) for setup.

👉 **Full CLI docs:** [**reposwarm-cli**](https://github.com/reposwarm/reposwarm-cli)

---

## What is RepoSwarm?

RepoSwarm automatically analyzes your entire codebase portfolio and generates standardized architecture documentation. Point it at your GitHub repos (or CodeCommit, GitLab, Azure DevOps, Bitbucket) and get back clean, structured `.arch.md` files — perfect as AI agent context, onboarding docs, or architecture reviews.

<p align="center">
  <img src="assets/banner-swarm.png" alt="RepoSwarm Agents" width="80%">
</p>

### ✨ Key Features

- 🔍 **AI-Powered Analysis** — Uses Claude to deeply understand codebases
- 📝 **Standardized Output** — Generates consistent `.arch.md` architecture files
- 🔄 **Incremental Updates** — Only re-analyzes repos with new commits
- 💾 **Smart Caching** — DynamoDB or file-based caching avoids redundant work
- 🎯 **Type-Aware Prompts** — Specialized analysis for backend, frontend, mobile, infra, and libraries
- 📦 **Results Hub** — All architecture docs committed to a centralized repository
- 🔌 **Multi-Provider** — Anthropic API, Amazon Bedrock, or LiteLLM proxy
- 🌐 **Multi-Git** — GitHub, GitLab, CodeCommit, Azure DevOps, Bitbucket

### 📋 See It In Action

Check out [RepoSwarm's self-analysis](https://github.com/royosherove/repo-swarm-sample-results-hub/blob/main/repo-swarm.arch.md) — RepoSwarm investigating its own codebase!

🎬 **Architecture Overview (click to play)**

[![▶ Watch on YouTube](https://img.youtube.com/vi/rOMf9xvpgtc/hqdefault.jpg)](https://www.youtube.com/watch?v=rOMf9xvpgtc)

---

## How It Works

<p align="center">
  <img src="assets/architecture.png" alt="RepoSwarm Architecture" width="100%">
</p>

**Pipeline:** Cache check → Clone → Type detection → Structure analysis → Prompt selection → AI analysis → Store results → Cleanup

---

## Common Workflows

### Run an Investigation

```bash
reposwarm repos add my-app --url https://github.com/org/my-app
reposwarm investigate my-app
reposwarm wf progress
reposwarm results read my-app
```

### Investigate All Repos in Parallel

```bash
reposwarm investigate --all --parallel 3
reposwarm dashboard
```

### Diagnose Issues

```bash
reposwarm doctor                       # Full health check
reposwarm errors                       # Stalls + failures
reposwarm wf retry <workflow-id>       # Re-run a failed investigation
```

### Search Across All Architecture Docs

```bash
reposwarm results search "authentication"
reposwarm results diff repo-a repo-b
reposwarm results export --all -d ./docs
```

👉 **Full command reference:** [**reposwarm-cli README**](https://github.com/reposwarm/reposwarm-cli)

---

## Configuration

### LLM Provider

```bash
reposwarm config provider setup        # Interactive (Anthropic, Bedrock, LiteLLM)
```

### Git Provider

```bash
reposwarm config git setup             # Interactive (GitHub, GitLab, CodeCommit, Azure, Bitbucket)
```

### Adding Repositories

```bash
reposwarm repos add my-backend --url https://github.com/org/my-backend
reposwarm repos add my-frontend --url https://github.com/org/my-frontend
reposwarm repos discover               # Auto-discover from your configured git provider (GitHub, GitLab, CodeCommit, Azure DevOps, Bitbucket)
```

Or edit `prompts/repos.json` directly:

```json
{
  "repositories": {
    "my-backend": {
      "url": "https://github.com/org/my-backend",
      "type": "backend",
      "description": "Main API service"
    }
  }
}
```

### Analysis Prompt Types

| Type | Focus | Prompts |
|------|-------|---------|
| 🔧 **Backend** | APIs, databases, services | [`prompts/backend/`](prompts/backend/) |
| 🎨 **Frontend** | Components, routing, state | [`prompts/frontend/`](prompts/frontend/) |
| 📱 **Mobile** | UI, device features, offline | [`prompts/mobile/`](prompts/mobile/) |
| 📚 **Libraries** | API surface, internals | [`prompts/libraries/`](prompts/libraries/) |
| ☁️ **Infrastructure** | Resources, deployments | [`prompts/infra-as-code/`](prompts/infra-as-code/) |
| 🔗 **Shared** | Security, auth, monitoring | [`prompts/shared/`](prompts/shared/) |

---

## Ecosystem

| Project | Description | Install / Pull |
|---------|-------------|----------------|
| ⌨️ [**reposwarm-cli**](https://github.com/reposwarm/reposwarm-cli) | CLI — setup, investigate, diagnose, results | `curl -fsSL .../install.sh \| sh` |
| 🔌 [**reposwarm-api**](https://github.com/reposwarm/reposwarm-api) | REST API server for repos, workflows, prompts | `docker pull ghcr.io/reposwarm/api:latest` |
| 📊 [**reposwarm-ui**](https://github.com/reposwarm/reposwarm-ui) | Next.js dashboard for browsing investigations | `docker pull ghcr.io/reposwarm/ui:latest` |
| 🤖 **reposwarm** (this repo) | Core engine — Temporal workflows + analysis | `docker pull ghcr.io/reposwarm/worker:latest` |
| 🧠 [**reposwarm-askbox**](https://github.com/reposwarm/reposwarm-askbox) | AI agent for querying architecture docs | `docker pull ghcr.io/reposwarm/askbox:latest` |
| 📋 [**sample-results-hub**](https://github.com/royosherove/repo-swarm-sample-results-hub) | Example output — generated `.arch.md` files | — |

All Docker images are multi-arch (`linux/amd64` + `linux/arm64`) and published automatically on every push to `main`.

---

## Project Structure

```
reposwarm/
├── prompts/                 # AI analysis prompts by repo type
│   ├── backend/            # API, database, service prompts
│   ├── frontend/           # UI, component, routing prompts
│   ├── mobile/             # Mobile app specific prompts
│   ├── libraries/          # Library/API prompts
│   ├── infra-as-code/      # Infrastructure prompts
│   ├── shared/             # Cross-cutting concerns
│   └── repos.json          # Repository configuration
├── src/
│   ├── investigator/       # Core analysis engine
│   │   └── core/          # Main analysis logic
│   ├── workflows/          # Temporal workflow definitions
│   ├── activities/         # Temporal activity implementations
│   ├── models/             # Data models and schemas
│   └── utils/              # Storage adapters and utilities
├── tests/                  # Unit and integration tests
└── temp/                   # Generated .arch.md files (local dev)
```

---

## Credits

RepoSwarm was born out of a hackathon at [Verbit](https://verbit.ai/), built by:
- [Moshe](https://github.com/mosher)
- [Idan](https://github.com/Idandos)
- [Roy](https://github.com/royosherove)

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

---

## Recent Fixes (2026-03-23)

### 🔧 DynamoDB Local — Table Creation Fails on Fresh Install

**Symptom:** `reposwarm repos add` returns 500 with "Request must contain either a valid AWS access key ID or X.509 certificate." `reposwarm doctor` shows `DynamoDB — DISCONNECTED` even though the container is running.

**Root cause:** The API server used a no-op SigV4 signer (`signer: { sign: async (req) => req }`) that stripped all auth headers. DynamoDB Local accepts unsigned requests for data operations (PutItem, GetItem) but rejects control plane operations (CreateTable, DescribeTable) with `MissingAuthenticationToken`. This caused `ensureTable()` to silently fail on startup — the table was never created, and all subsequent operations returned 500.

**Fix:** Removed the no-op signer. DynamoDB Local needs valid SigV4 signatures but doesn't verify the actual credentials — dummy static credentials with normal signing work fine.

**Update:** `docker compose pull api && docker compose up -d api`

### 🔧 Anthropic Provider — API Key Not Written to worker.env

**Symptom:** After running `reposwarm config provider setup` with the Anthropic provider, the `ANTHROPIC_API_KEY` was never written to `worker.env`. Investigations fail with authentication errors even though the key was entered during setup.

**Fix:** Added `APIKey` field to the provider config struct, added `--api-key` flag and interactive prompt, and wired it through to `WorkerEnvVars()` for Anthropic.

**Update:** `curl -fsSL https://raw.githubusercontent.com/reposwarm/reposwarm-cli/main/install.sh | sh`

### 🔧 Provider Switch — Stale Bedrock Env Vars Survive

**Symptom:** Switching from Bedrock to Anthropic (or vice versa) left stale environment variables (`CLAUDE_CODE_USE_BEDROCK=1`, `CLAUDE_PROVIDER=bedrock`) in `worker.env`, causing the worker to stay in Bedrock mode.

**Fix:** Added provider-aware cleanup to `writeWorkerEnvForProvider()` — removes exclusive env vars from other providers when switching.

### 🔧 DynamoDB Local — Fails on Machines Without AWS Credentials

**Symptom:** On fresh EC2 instances or machines without IAM roles or `~/.aws/credentials`, the API and worker containers fail because the AWS SDK tries to resolve credentials via IMDS and hangs.

**Fix:** Added dummy `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` defaults to API, worker, and UI services in the Docker Compose template. DynamoDB Local accepts any credentials.

### 2026-03-24

#### 🔧 UI: Repos added via CLI now visible in dashboard

**Symptom:** Repos added with `reposwarm repos add` appeared in the CLI but not in the web UI on Docker installs.

**Root cause:** The UI container had no way to reach the API container — `/v1/*` requests from the browser were hitting the UI's own Next.js server, which had no route for them.

**Fix:** Added Next.js rewrites to proxy `/v1/*` requests from the UI container to the API container. Repos added via CLI now appear immediately in the dashboard.

**Update:** `docker compose pull ui && docker compose up -d ui`

#### 🔧 CLI: `doctor` correctly detects provider credentials on Docker installs

**Symptom:** `reposwarm doctor` reported `ANTHROPIC_API_KEY — NOT SET` even when the key was correctly configured in `worker.env`.

**Root cause:** On Docker installs, `doctor` was querying the API container for environment variable status. The API container doesn't have access to `worker.env` — only the worker container does. So the key always appeared missing.

**Fix:** `reposwarm doctor` now reads `worker.env` directly from the local filesystem instead of querying the API container.

**Update:** `curl -fsSL https://raw.githubusercontent.com/reposwarm/reposwarm-cli/main/install.sh | sh`

#### 🔧 UI: Auto-Discover is now provider-agnostic

**Symptom:** The "Auto-Discover from CodeCommit" button implied discovery only worked with AWS CodeCommit.

**Fix:** Button text updated to "Auto-Discover". Discovery works with GitHub, GitLab, Azure DevOps, Bitbucket, and CodeCommit based on your configured git provider. Multi-provider auto-discovery across all supported git providers is coming imminently.

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
