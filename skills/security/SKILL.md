---
name: security
description: Client and backend security, privacy boundaries, and credential safety rules
---

# Purpose

Guarantees absolute credential safety, user privacy, and zero data leakage.

# Scope

API keys, authentication tokens, audio storage, network encryption, and platform keystores.

# When to use

Use whenever handling authentication, storing user settings, transmitting data, or configuring API keys.

# Architecture rules

- **Zero Client Credentials**: Sarvam AI API keys must NEVER exist in client source code, APKs, or app bundles.
- All network communication with the backend must use HTTPS / WSS in production.
- **Transient Audio**: Spoken audio is transient and must NEVER be persisted to disk or unencrypted storage without explicit user consent.

# Preferred patterns

- Load secrets via backend environment variables (`src/app/core/config.py`).
- Use platform secure storage (Android EncryptedSharedPreferences / KeyStore, iOS Keychain) for sensitive client tokens.
- Obfuscate and sanitize all logs to ensure raw user speech is never emitted at production log levels.

# Anti-patterns

- ❌ Hardcoding API keys, passwords, or secrets anywhere in git-tracked files.
- ❌ Storing unencrypted audio or transcript history locally without consent.
- ❌ Trusting client-side input validation on the backend.

# Testing requirements

- Verify that `git status` never tracks `.env` or credential files.
- Automated security audits of dependencies.

# Platform considerations

- Android Keystore and iOS Keychain provide hardware-backed security for authentication tokens.

# Related documentation

- [AGENTS.md](../../AGENTS.md)
