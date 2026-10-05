---
name: testing
description: Testing strategies, test double patterns, and test execution rules across KMP and backend
---

# Purpose

Defines test suites, test doubles, and verification standards for Effortless.

# Scope

Unit tests in `src/tests/`, and contract validations.

# When to use

Use whenever writing new features, modifying use cases, updating mappers, or refactoring business logic.

# Architecture rules

- Shared business logic must have dedicated unit tests in `commonTest`.
- Tests must never make live network calls or connect to external production APIs.
- Use fake repositories (`FakeTranslationRepository`) rather than dynamic mocking frameworks in shared code.

# Preferred patterns

- Fast, deterministic tests using `kotlinx.coroutines.test.runTest`.
- Structure tests with Arrange-Act-Assert.
- Test error conditions and validation boundaries (e.g. empty strings, unsupported language pairs).

# Anti-patterns

- ❌ Testing implementation details instead of public behavior.
- ❌ Flaky tests depending on wall-clock time or real network delays.
- ❌ Writing tests that only run on a single platform when they could run in `commonTest`.

# Testing requirements

- Run shared tests: `./gradlew :shared:allTests`.
- Run backend tests: `poetry run pytest`.

# Platform considerations

- `commonTest` runs on both JVM (Desktop) and native iOS Simulator environments.

# Related documentation

- [skills/clean-architecture/SKILL.md](../clean-architecture/SKILL.md)
