# Desktop Architecture

## Overview

Desktop support provides system-level speech-to-translation input. Unlike mobile keyboard extensions, desktop implementation must handle global text insertion into any active application.

## Platform Approaches

### macOS

- **Audio**: `AVAudioEngine` (same as iOS, but no extension restrictions)
- **Text insertion**: Accessibility API (`AXUIElement`) or `CGEvent` key injection
- **System integration**: Menu bar app or system service
- **Permissions**: Microphone permission + Accessibility permission

### Windows

- **Audio**: WASAPI or Windows.Media.Capture
- **Text insertion**: `SendInput()` WIN32 API or UI Automation
- **System integration**: System tray application
- **Permissions**: Standard app permissions

### Linux

- **Audio**: PulseAudio/PipeWire
- **Text insertion**: `xdotool` / `ydotool` (X11/Wayland) or IBus/Fcitx input method
- **System integration**: System tray application
- **Permissions**: Standard user permissions

## KMP Desktop Architecture

```
desktopApp/
├── src/
│   ├── main/
│   │   ├── kotlin/
│   │   │   ├── Main.kt                 # Entry point
│   │   │   ├── ui/
│   │   │   │   ├── FloatingPanel.kt     # Overlay UI (Compose Desktop)
│   │   │   │   └── SystemTray.kt        # Tray icon + menu
│   │   │   ├── audio/
│   │   │   │   └── DesktopAudioRecorder.kt
│   │   │   └── input/
│   │   │       └── TextInsertion.kt     # expect/actual per OS
│   │   └── resources/
│   └── test/
```

## Interaction Flow

```
System tray icon
    │
    ├── Click → Show floating panel
    │       │
    │       ├── Language selector
    │       ├── Mic button
    │       └── Status indicator
    │
    ├── Hotkey (e.g., Ctrl+Shift+T)
    │       │
    │       ▼
    │   Start recording
    │       │
    │       ▼
    │   Process via backend (same as mobile)
    │       │
    │       ▼
    │   Insert translated text into active application
    │       │
    │       ▼
    │   Text appears in whatever app has focus
    │
    └── Settings → Configure languages, hotkeys, preferences
```

## Key Differences from Mobile

| Aspect | Mobile | Desktop |
|---|---|---|
| **Input target** | Active text field (keyboard context) | Any application (global) |
| **Text insertion** | IME/keyboard extension API | OS-level text injection |
| **Activation** | Mic button on keyboard | Hotkey or tray icon |
| **Always visible** | While keyboard is open | Tray icon + floating panel |
| **Permissions** | Mic permission | Mic + Accessibility |

## Priority

Desktop is the lowest priority platform (Phase 9). Mobile keyboard is the primary product.
