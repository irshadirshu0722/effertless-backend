---
name: ios-keyboard
description: iOS Custom Keyboard Extension and text insertion architecture
---

# Purpose
Guides implementation of the Effortless custom keyboard extension on iOS.

# Scope
iOS Keyboard Extension, `UIInputViewController`, `textDocumentProxy`, and App Group shared memory.

# When to use
Use when developing or updating the iOS keyboard extension target in Xcode.

# Architecture rules
- The iOS keyboard runs in a memory-constrained app extension (typically ~30MB limit).
- The extension imports `Shared.framework` for business logic, or communicates via an App Group container.
- Text insertion is performed via `textDocumentProxy.insertText(text)`.

# Preferred patterns
- Native SwiftUI or UIKit keyboard interface if memory limits prevent heavy Compose runtimes in the extension process.
- Reusing pure KMP business logic from `:shared` without UI coupling.
- Requesting "Open Access" only when network communication is required.

# Anti-patterns
- ❌ Exceeding iOS extension memory limits (results in immediate OS termination).
- ❌ Trying to run desktop or heavy JVM libraries inside the iOS extension.

# Testing requirements
- Verify extension launch and memory footprints in Xcode Instruments.

# Platform considerations
- Must configure `NSExtension` in the extension's Info.plist with `IsASCIICapable` and `RequestsOpenAccess`.

# Related documentation
- [skills/architecture/SKILL.md](../architecture/SKILL.md)
