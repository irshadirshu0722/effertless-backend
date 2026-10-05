---
name: desktop
description: Desktop JVM architecture, packaging, and input integration rules
---

# Purpose
Guides Desktop JVM execution, native packaging, and OS input integration for Effortless.

# Scope
Desktop JVM target (`desktopMain`), Compose for Desktop, packaging tasks (DMG, MSI, DEB), and desktop input methods.

# When to use
Use when working on desktop UI, system tray integration, keyboard global hotkeys, or desktop distribution builds.

# Architecture rules
- Desktop entry point is in `client/shared/src/desktopMain/kotlin/com/effortless/Main.kt`.
- Use the CIO engine for Desktop Ktor networking.
- Window management and lifecycle must adhere to Jetpack Compose Desktop conventions.

# Preferred patterns
- Clean window sizing and responsive layouts adapted for mouse and keyboard navigation.
- Package distributions using `./gradlew :shared:packageDistributionForCurrentOS`.

# Anti-patterns
- ❌ Relying on mobile touch gestures without keyboard/mouse alternatives.
- ❌ Hardcoding absolute local file paths.

# Testing requirements
- Test desktop compilation via `./gradlew :shared:desktopJar` and `./gradlew :shared:desktopTest`.

# Platform considerations
- macOS, Windows, and Linux supported via Java 17+ and Skiko graphics engine.

# Related documentation
- [skills/compose-multiplatform/SKILL.md](../compose-multiplatform/SKILL.md)
