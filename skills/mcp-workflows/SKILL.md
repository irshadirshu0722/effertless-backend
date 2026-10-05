---
name: mcp-workflows
description: Guidelines and policies for using MCP tools safely across GitHub, Android, Docker, and Database services.
---

# MCP Workflows & Tool Guidelines

This skill defines rules and procedures for interacting with Model Context Protocol (MCP) servers and external tools in the Effortless repository.

---

## 1. Principles of Least Privilege

1. **Read-Only Default**: Always use read operations when inspecting states. Never execute write or mutation operations unless explicitly requested by the user.
2. **Never Autonomous Destructive Actions**:
   - Never run `git push --force` or modify protected branches.
   - Never execute `docker compose down -v` without explicit user request.
   - Never execute SQL `DROP`, `TRUNCATE`, or destructive migrations.
   - Never execute Redis `FLUSHALL` or `FLUSHDB`.
3. **No Secret Ingestion**: Do not pass sensitive production tokens, credentials, or API keys into MCP inputs or prompt logs.

---

## 2. GitHub MCP Workflow

When using GitHub MCP tools:

- **Issues & PRs**: Retrieve context, analyze review feedback, inspect diffs.
- **Branch Management**:
  - Always work in branches matching `feature/*`, `fix/*`, or `chore/*`.
  - Never attempt to merge into `main` or `master` without explicit human authorization.
- **Commits**: Follow conventional commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).

---

## 3. Android & ADB Workflow (via ARTEMIS or CLI)

When automating or testing on an Android device:

1. **Device Check**: Verify that target device is available (`adb devices`).
2. **Build First**: Ensure debug APK is freshly compiled before deploying.
3. **Logcat Capture**: Isolate logs to the application process (`--pid`) to avoid noise.
4. **Visual Inspection**: Pull screenshots or accessibility node hierarchies to verify UI states before concluding tests.

---

## 4. Database & Cache Inspection Workflow

- **PostgreSQL**:
  - Use `docker compose exec -T postgres psql -U postgres -d effortless -c "\dt"` to inspect schemas.
  - Run `SELECT` queries only for debugging local development data.
- **Redis**:
  - Use `docker compose exec -T redis redis-cli ping` or `KEYS *` to inspect active session keys.
  - Never run `FLUSHALL`.

---

## 5. Docker Diagnostics Workflow

When debugging container health or startup issues:

1. Check status: `docker compose ps`
2. Check container logs: `docker compose logs <service>`
3. Check health: verify `/health` and `/health/ready` on the backend.
