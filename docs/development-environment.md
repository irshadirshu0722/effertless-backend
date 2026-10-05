# Effortless — AI-Native Development Environment & MCP Architecture

This document defines the development environment, tooling strategy, and Model Context Protocol (MCP) integrations for the **Effortless** monorepo across Kotlin Multiplatform, Compose Multiplatform, Android, iOS, Desktop, and Python FastAPI.

---

## Table of Contents

1. [Guiding Principles & Minimalist Strategy](#1-guiding-principles--minimalist-strategy)
2. [MCP Inventory & Evaluation Matrix](#2-mcp-inventory--evaluation-matrix)
3. [GitHub Integration & Workflow](#3-github-integration--workflow)
4. [Android Development & Tooling](#4-android-development--tooling)
   - [Google ARTEMIS](#google-artemis)
   - [Native ADB Platform Tools](#native-adb-platform-tools)
   - [Android Debugging Runbook](#android-debugging-runbook)
5. [Chucker Network Debugging & Ktor Chain](#5-chucker-network-debugging--ktor-chain)
6. [PostgreSQL & Redis Development Tooling](#6-postgresql--redis-development-tooling)
7. [Docker & Container Diagnostics](#7-docker--container-diagnostics)
8. [Python & FastAPI Backend Tooling](#8-python--fastapi-backend-tooling)
9. [Kotlin Multiplatform & Compose Multiplatform Tooling](#9-kotlin-multiplatform--compose-multiplatform-tooling)
10. [Realtime WebSocket Debugging & State Machine](#10-realtime-websocket-debugging--state-machine)
11. [Git Workflow & Commit Standards](#11-git-workflow--commit-standards)
12. [Local Development Commands Reference](#12-local-development-commands-reference)

---

## 1. Guiding Principles & Minimalist Strategy

To maintain high development velocity, security, and stability, Effortless follows these core principles:

- **Do Not Overinstall**: We do not install redundant, obsolete, or experimental MCP servers when the native IDE or environment already provides direct, secure, and performant capabilities.
- **Native Antigravity Capabilities First**:
  - **Filesystem**: Antigravity natively provides robust filesystem inspection and editing (`view_file`, `list_dir`, `grep_search`, `write_to_file`, `replace_file_content`). A separate filesystem MCP is redundant.
  - **Web Research**: Antigravity natively provides `search_web` and `read_url_content` for accessing official documentation in realtime.
  - **Terminal / Shell**: Antigravity natively provides `run_command` with direct access to local CLI utilities (`adb`, `git`, `docker`, `uv`, `gradlew`, `psql`, `redis-cli`).
  - **Browser Automation**: Antigravity provides native `browser_subagent` for interactive web sessions.
- **Official & Maintained**: If an MCP is adopted, it must be officially maintained by the vendor, under an active open-source license, and conform to the least-privilege security model.
- **Zero Secrets Committed**: Provider keys (Sarvam AI), private database credentials, and GitHub personal access tokens must never be hard-coded or committed to git.

---

## 2. MCP Inventory & Evaluation Matrix

| MCP / Tool                           | Purpose                                             | Status in Effortless                                  | Scope     | Rationale / Recommendation                                                                                                                                                    |
| ------------------------------------ | --------------------------------------------------- | ----------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GitHub MCP Server**                | Repository, PRs, issues, commits, reviews           | **Configured** (`ghcr.io/github/github-mcp-server`)   | Dev / VCS | The npm package `@modelcontextprotocol/server-github` was deprecated in April 2025. We configure the official GitHub-maintained Docker image with read-only scopes.           |
| **Android Tooling (Google ARTEMIS)** | Natural-language Android device/emulator automation | **Configured** (`google/artemis`)                     | Android   | Open-source framework released August 2026 by Google Pixel Test Engineering. Provides visual targeting, accessibility helper, and MCP server for assistants.                  |
| **Android ADB CLI**                  | Device management, Logcat, APK installation         | **Active** (Native CLI via `run_command`)             | Android   | Standard Android Platform Tools (`~/Library/Android/sdk/platform-tools/adb`) natively accessible for immediate debugging.                                                     |
| **Filesystem MCP**                   | Local workspace file access                         | **Omitted**                                           | Core      | Redundant. Antigravity provides native, faster, and more granular file manipulation tools.                                                                                    |
| **Web Research MCP**                 | Realtime docs & library research                    | **Active** (Native Web Search)                        | Docs      | Redundant to add external MCP. Native `search_web` queries official sources (`developer.android.com`, `kotlinlang.org`, `ktor.io`, `fastapi.tiangolo.com`, `docs.sarvam.ai`). |
| **PostgreSQL Tooling**               | Schema and data inspection                          | **Active** (Docker CLI via `psql`)                    | Backend   | Accessible via `docker compose exec postgres psql`. External DB MCP is optional; CLI is safer to prevent automated destructive queries.                                       |
| **Redis Tooling**                    | Cache and session key inspection                    | **Active** (Docker CLI via `redis-cli`)               | Backend   | Accessible via `docker compose exec redis redis-cli`. Prevents accidental `FLUSHALL`.                                                                                         |
| **Docker Tooling**                   | Container and health inspection                     | **Active** (Native CLI via `docker`)                  | Infra     | Native `docker` and `docker compose` commands provide complete observability.                                                                                                 |
| **Browser / Playwright**             | Web dashboard testing                               | **Optional / On-Demand**                              | Web UI    | Native `browser_subagent` is available. Playwright should only be added if Effortless builds a customer-facing Web app.                                                       |
| **iOS / Xcode Tooling**              | iOS simulator build and test                        | **Active** (macOS CLI via `xcodebuild` / `./gradlew`) | iOS       | Directly driven on macOS via Gradle iOS simulator targets (`:shared:iosSimulatorArm64Test`).                                                                                  |

---

## 3. GitHub Integration & Workflow

Configuration path: `.agents/plugins/effortless-dev/mcp_config.json`

### Supported Capabilities

- **Issues & PRs**: Inspect descriptions, discussions, linked bugs, and acceptance criteria.
- **Code Review**: Read reviewer comments and analyze diffs.
- **Commits & Branches**: Understand git history across `feature/*` and `fix/*` branches.

### Security Constraints (Rule 7 & MCP Security Policy)

- The GitHub MCP operates with **least-privilege read permissions** by default.
- **No Autonomous Merging**: The AI agent is strictly prohibited from merging pull requests or pushing directly to protected branches (`main`, `master`) without explicit user review and confirmation.
- **Authentication**: Uses `GITHUB_PERSONAL_ACCESS_TOKEN` loaded from host environment variables, never committed to git.

---

## 4. Android Development & Tooling

Effortless combines Google's official agent framework (**Google ARTEMIS**) with battle-tested native **ADB platform tools**.

### Google ARTEMIS

- **Source**: [google/artemis](https://github.com/google/artemis) (Open-source Apache 2.0, released August 2026 by Google Pixel Test Engineering).
- **Architecture**: A Python-based agent framework that exposes an MCP server interface to coding assistants like Antigravity, Claude Code, and Cursor.
- **Capabilities**:
  - **Natural Language Actions**: Instruct the agent in plain language ("Open Settings, find Battery, and report percentage").
  - **Flash Mode**: Fast observe-and-act loop (3–5 seconds per step).
  - **Pro Mode**: In-depth planning, pre-action verification, and post-action assertions.
  - **Accessibility Helper**: Automatically installs a lightweight helper on the emulator to parse screen hierarchies and accessibility nodes.

### Native ADB Platform Tools

ADB is located on macOS at `~/Library/Android/sdk/platform-tools/adb`.

Common operations used during agent workflows:

```bash
# Verify attached devices or running emulators
adb devices -l

# Install freshly built debug APK
adb install -r client/androidApp/build/outputs/apk/debug/androidApp-debug.apk

# Launch the Effortless main activity
adb shell am start -n com.effortless.app/.MainActivity

# Capture logcat filtered by app PID
adb logcat --pid=$(adb shell pidof -s com.effortless.app)

# Capture screenshot for visual inspection
adb exec-out screencap -p > /tmp/screen.png

# Grant microphone permission for voice translation testing
adb shell pm grant com.effortless.app android.permission.RECORD_AUDIO
```

### Android Debugging Runbook

```text
User Issue / Task
       ↓
1. ./gradlew :androidApp:assembleDebug
       ↓
2. adb install -r <apk>
       ↓
3. adb shell am start -n com.effortless.app/.MainActivity
       ↓
4. Inspect UI (screencap / uiautomator dump / ARTEMIS)
       ↓
5. Inspect Logcat (adb logcat -s KtorClient:D Effortless:D)
       ↓
6. Inspect HTTP payloads via Chucker notification
       ↓
7. Fix code in client/
       ↓
8. Re-test and verify
```

---

## 5. Chucker Network Debugging & Ktor Chain

Effortless integrates **Chucker** directly into the Android networking stack for on-device HTTP inspection.

### Architecture

```text
Compose UI (HomeScreen)
   │
   ▼
HomeViewModel (StateFlow)
   │
   ▼
TranslateTextUseCase
   │
   ▼
TranslationRepository (TranslationRepositoryImpl)
   │
   ▼
TranslationApiService
   │
   ▼
Ktor HttpClient
   │
   ▼
OkHttp Engine (PlatformEngine.android.kt)
   │
   ▼
AndroidNetworkConfig (Interceptors)
   │
   ▼
ChuckerInterceptor (Debug Only)
   │  ├── Header Redaction: Authorization, X-API-Key, Cookie, Set-Cookie
   │  └── Max payload: 250 KB
   ▼
Effortless FastAPI Backend (http://10.0.2.2:8000 or http://localhost:8000)
```

### Safety & Release Isolation (Rule 14 & Rule 8)

- **Debug Builds**: `com.github.chuckerteam.chucker:library:4.1.0` records HTTP requests and displays an in-app notification and inspection activity.
- **Release Builds**: `com.github.chuckerteam.chucker:library-no-op:4.1.0` compiles with zero overhead, empty method bodies, and completely excludes the inspection UI.
- **Header Redaction**: Configured in `EffortlessApplication.kt` with:
  ```kotlin
  .redactHeaders("Authorization", "X-API-Key", "Cookie", "Set-Cookie")
  ```
- **Privacy**: Raw audio buffers and sensitive transcripts are never stored in plain text.

---

## 6. PostgreSQL & Redis Development Tooling

PostgreSQL and Redis run locally inside Docker Compose (`docker-compose.yml`).

### PostgreSQL Safe Inspection

To inspect the local development database:

```bash
# Connect to PostgreSQL CLI in the container
docker compose exec -T postgres psql -U postgres -d effortless

# Common safe inspection queries:
\dt                  # List tables
\d <table_name>      # Describe table schema
SELECT COUNT(*) FROM <table_name>;
```

> [!CAUTION]
> **Database Safety Policy**: The AI agent must never autonomously execute `DROP`, `TRUNCATE`, or destructive migration commands. Production databases are always managed cloud services (Rule 4) and isolated from direct agent write access.

### Redis Safe Inspection

To inspect local cache and realtime session keys:

```bash
# Check connectivity
docker compose exec -T redis redis-cli ping

# Inspect keys (local dev only)
docker compose exec -T redis redis-cli keys "*"

# Inspect memory usage
docker compose exec -T redis redis-cli info memory
```

> [!WARNING]
> Never execute `FLUSHALL` or `FLUSHDB` in any environment without explicit user approval.

---

## 7. Docker & Container Diagnostics

The local infrastructure consists of:

- `effortless-postgres` (Port 5432)
- `effortless-redis` (Port 6379)
- `effortless-backend` (Port 8000)

### Troubleshooting Workflow

```text
Backend Cannot Connect to DB/Redis
                ↓
1. Check container health status:
   docker compose ps
                ↓
2. If unhealthy or restarting, inspect logs:
   docker compose logs postgres
   docker compose logs redis
                ↓
3. Check host port conflicts (e.g. native brew postgres):
   lsof -i :5432
                ↓
4. Verify readiness probe:
   curl http://localhost:8000/health/ready
```

---

## 8. Python & FastAPI Backend Tooling

- **Package & Dependency Manager**: `uv` (Fast, reproducible virtualenv & locking).
- **Linter & Formatter**: `Ruff` (Single tool for linting and formatting; replaces Black, Flake8, and isort).
- **Test Framework**: `pytest` with `pytest-asyncio`.
- **Settings & Validation**: `Pydantic` and `Pydantic Settings`.

### Developer Commands

```bash
cd backend

# Lint check
poetry run ruff check .

# Format check
poetry run ruff format --check .

# Auto-format
poetry run ruff format .

# Run test suite
poetry run pytest
```

---

## 9. Kotlin Multiplatform & Compose Multiplatform Tooling

- **Build System**: Gradle 9 with Version Catalogs (`client/gradle/libs.versions.toml`).
- **Architectural Layers**:
  - `domain`: Pure Kotlin, zero platform or framework dependencies (Rule 13).
  - `data`: Ktor HTTP client, DTOs, mappers, repositories.
  - `presentation`: Compose Multiplatform, ViewModel (`StateFlow`).
  - `androidApp` / `iosApp` / `desktopApp`: Platform-specific entry points.

### Compose Debugging Guidelines

1. **State Flow**: State flows unidirectional down from `ViewModel` via `StateFlow<UIState>`.
2. **Recomposition**: Avoid allocating lambdas or objects directly inside Composable scopes without `remember`.
3. **Threading**: Heavy I/O (speech recording, network calls) must run on `Dispatchers.IO` or `Dispatchers.Default`, never blocking `Dispatchers.Main`.

---

## 10. Realtime WebSocket Debugging & State Machine

For upcoming streaming speech-to-translation, Effortless enforces an explicit state machine:

```text
               ┌───────────────┐
               │     IDLE      │◄────────────────┐
               └───────┬───────┘                 │
                       │ user initiates          │
                       ▼                         │
               ┌───────────────┐                 │
               │  CONNECTING   │                 │
               └───────┬───────┘                 │
                       │ socket open             │
                       ▼                         │
               ┌───────────────┐                 │
               │   LISTENING   │                 │
               └───────┬───────┘                 │
                       │ audio streaming         │
                       ▼                         │
               ┌───────────────┐                 │
               │ TRANSCRIBING  │                 │
               └───────┬───────┘                 │
                       │ interim transcript      │
                       ▼                         │
               ┌───────────────┐                 │
               │  TRANSLATING  │                 │
               └───────┬───────┘                 │
                       │ final text received     │
                       ▼                         │
               ┌───────────────┐                 │
               │   COMPLETED   ├─────────────────┘
               └───────────────┘

Transitions to ERROR, RECONNECTING, or CANCELLED can occur from any active state.
```

---

## 11. Git Workflow & Commit Standards

### Branching Strategy

- `main` / `master`: Production-ready code. Protected branch.
- `feature/<name>`: New capabilities (e.g. `feature/translation-mvp`).
- `fix/<name>`: Bug fixes (e.g. `fix/websocket-reconnect`).
- `chore/<name>`: Tooling, dependencies, refactoring.

### Commit Conventions

Follow Conventional Commits:

```text
feat: add translation repository
fix: handle websocket reconnect
chore: configure ruff and docker
test: add translation use case tests
build: update chucker dependency
ci: add backend github actions workflow
```

---

## 12. Local Development Commands Reference

| Action                       | Makefile Target     | Raw Command                                              |
| ---------------------------- | ------------------- | -------------------------------------------------------- |
| **Start Postgres & Redis**   | `make infra-up`     | `docker compose up -d postgres redis`                    |
| **Stop Infrastructure**      | `make infra-down`   | `docker compose down`                                    |
| **Reset Local Data**         | `make infra-clean`  | `docker compose down -v`                                 |
| **Run Full Stack in Docker** | `make up`           | `docker compose up -d`                                   |
| **Run FastAPI Locally**      | `make dev-backend`  | `cd backend && poetry run uvicorn app.main:app --reload` |
| **Backend Tests**            | `make test-backend` | `cd backend && poetry run pytest`                        |
| **Backend Lint Check**       | `make lint-backend` | `cd backend && poetry run ruff check .`                  |
| **Client Desktop Tests**     | `make test-client`  | `cd client && ./gradlew :shared:desktopTest`             |
| **Build Android Debug APK**  | —                   | `cd client && ./gradlew :androidApp:assembleDebug`       |
| **Build Desktop JAR**        | —                   | `cd client && ./gradlew :shared:desktopJar`              |
