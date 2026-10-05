# Effortless — MCP & Tooling Security Policy

This document establishes the security boundaries, categorization, and operational constraints for Model Context Protocol (MCP) servers and external developer tools used across the Effortless repository.

---

## 1. Core Security Principles

1. **Least Privilege**: Tools and agents receive only the minimal permissions required to complete local development tasks.
2. **Read-Only by Default**: Discovery, inspection, and analysis operations default to read-only access.
3. **Zero Secrets in Code or Logs (Rule 7)**: No tool may emit or record API keys, auth tokens, database passwords, or private tokens in source code, logs, or unencrypted local caches.
4. **Human-in-the-Loop for High-Impact Actions**: Merging PRs to protected branches, modifying production cloud infrastructure, rotating credentials, or executing destructive database queries require explicit user authorization.

---

## 2. Tool Classification Tiers

Every tool and MCP server is categorized into one of three security tiers:

```text
 ┌───────────────────────────────────────────────────────────────┐
 │                            SAFE                               │
 │   Read-only inspection, file viewing, web research, linting   │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
 ┌───────────────────────────────▼───────────────────────────────┐
 │                         CONTROLLED                            │
 │   Local code edits, dev builds, emulator actions, dev DB      │
 └───────────────────────────────┬───────────────────────────────┘
                                 │
 ┌───────────────────────────────▼───────────────────────────────┐
 │                          SENSITIVE                            │
 │   Production credentials, secrets, branch merges, deployments │
 └───────────────────────────────────────────────────────────────┘
```

---

## 3. Inventory & Categorization Matrix

| Tool / Integration          | Tier         | Access Scope           | Allowed Operations                                         | Restricted / Prohibited Operations                         |
| --------------------------- | ------------ | ---------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| **Antigravity Filesystem**  | `CONTROLLED` | Local workspace        | Read/write files in `effortless/`                          | Modifying files outside workspace or in `.git/`            |
| **Native Web Search**       | `SAFE`       | Public internet        | Query official documentation and technical specs           | Exfiltrating internal code or private tokens               |
| **GitHub MCP Server**       | `CONTROLLED` | Repository             | Read issues, PRs, review comments, diffs, branch status    | Merging PRs, force-pushing, modifying repo admin settings  |
| **Google ARTEMIS / ADB**    | `CONTROLLED` | Local Android emulator | Install dev APK, read Logcat, take screenshots, UI actions | Interacting with unapproved external or production devices |
| **Chucker (Android)**       | `CONTROLLED` | Android debug process  | Inspect local HTTP requests, timing, status codes          | Must be disabled in release (`no-op`); redacted headers    |
| **Docker Engine & Compose** | `CONTROLLED` | Local Docker daemon    | Start/stop/inspect local `postgres`, `redis`, `backend`    | Wiping volumes (`-v`) without prompt; host daemon escapes  |
| **PostgreSQL Dev CLI**      | `CONTROLLED` | Local container DB     | `SELECT`, `EXPLAIN`, `\dt`, `\d` on local dev data         | Autonomous `DROP`, `TRUNCATE`, or connecting to prod       |
| **Redis Dev CLI**           | `CONTROLLED` | Local container cache  | `PING`, `KEYS`, `INFO`, `GET` on local cache               | `FLUSHALL`, `FLUSHDB`, or unconstrained production flush   |
| **Sarvam AI Provider**      | `SENSITIVE`  | Backend API            | Server-side translation/speech synthesis requests          | Never exposed to client, never logged at INFO/DEBUG        |
| **GitHub Token**            | `SENSITIVE`  | GitHub API             | Authenticating developer PR/issue interactions             | Committing token to git or embedding in Dockerfile         |

---

## 4. Specific Tool Policies

### A. GitHub Integration Policy

- **Image**: Official `ghcr.io/github/github-mcp-server`.
- **Token**: Loaded strictly via `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable.
- **Allowed**:
  - Reading repository file trees and commits.
  - Reading open pull requests and review comments.
  - Creating draft PRs or reading issue descriptions.
- **Prohibited**:
  - Merging pull requests into `main` or `master`.
  - Deleting remote branches.
  - Modifying branch protection rules.

### B. Android & Mobile Tooling Policy (ADB & ARTEMIS)

- **Local Scope**: ADB and Google ARTEMIS connect strictly to `localhost` or USB-connected development devices.
- **Accessibility Helper**: Installs only the standard Google accessibility testing helper on local emulators.
- **Permission Boundaries**: Audio recording permissions (`RECORD_AUDIO`) are granted explicitly on emulators for testing voice pipelines; never bypass system prompts on user-owned physical production devices without consent.

### C. Chucker Network Inspection Policy

- **Debug Build Guarantee**: Chucker must only ever be referenced as `debugImplementation(libs.chucker.library)` in `androidApp/build.gradle.kts`.
- **Release No-Op Guarantee**: Release builds must link `releaseImplementation(libs.chucker.library.noop)`, which removes all recording logic and compiles to empty stubs.
- **Header Redaction**: The following headers are permanently redacted in `EffortlessApplication.kt`:
  - `Authorization`
  - `X-API-Key`
  - `Cookie`
  - `Set-Cookie`

### D. Database & Cache Safety Policy

- **Dev Isolation**: The database in Docker Compose uses throwaway developer credentials (`postgres` / `postgres`).
- **Query Guardrails**: Agents must not execute destructive DDL (`DROP DATABASE`, `DROP TABLE`, `ALTER TABLE ... DROP COLUMN`) or data wipes without an explicit request from the user.
- **Production Independence**: Production databases will be managed cloud instances (e.g. AWS Aurora / GCP Cloud SQL) accessible only via private VPC peering and locked down by role-based IAM.

---

## 5. Violation Handling & Enforcement

If any tool, script, or agent action encounters a security rule conflict:

1. **Halt Execution**: Stop the operation immediately before writing state.
2. **Notify User**: Explicitly explain why the operation was halted (e.g. attempted destructive operation or missing credential).
3. **Require Approval**: Request manual confirmation before proceeding with any action in the `SENSITIVE` tier.
