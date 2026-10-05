---
name: android-keyboard
description: Android InputMethodService and system keyboard integration guidelines
---

# Purpose
Guides integration of Effortless as a system-wide Android Input Method Editor (IME).

# Scope
Android `InputMethodService`, `InputConnection`, text insertion, and keyboard lifecycle.

# When to use
Use when developing or modifying the Android keyboard service and text insertion surface.

# Architecture rules
- The Android keyboard service must live in `:androidApp` or a dedicated `:androidKeyboard` module, depending strictly on `:shared` for business logic.
- Keep keyboard UI decoupled from the standalone app container.
- Text insertion must use `InputConnection.commitText(text, 1)`.

# Preferred patterns
- Lightweight View or ComposeView embedded in `InputMethodService.onCreateInputView()`.
- Use `KeyboardInput` abstraction defined in `commonMain`.
- Graceful handling of IME switches and hardware back button events.

# Anti-patterns
- ❌ Coupling core translation logic directly to Android `InputMethodService`.
- ❌ Blocking the Android IME main thread during network or speech processing.

# Testing requirements
- Test text committing and deletion with Android test harness or instrumented tests.

# Platform considerations
- Manifest must declare `<service android:name=".KeyboardService" android:permission="android.permission.BIND_INPUT_METHOD">`.

# Related documentation
- [skills/architecture/SKILL.md](../architecture/SKILL.md)
