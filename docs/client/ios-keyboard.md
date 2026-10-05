# iOS Keyboard Architecture

## Overview

The iOS Typeless keyboard is implemented as a Custom Keyboard Extension using `UIInputViewController`. Due to Apple's keyboard extension restrictions, the architecture differs significantly from Android.

## Key Constraints

| Constraint | Impact |
|---|---|
| **No full network access by default** | Must request "Allow Full Access" from user |
| **Limited memory** (~50 MB) | Cannot load large models or buffers |
| **No background execution** | Processing stops when keyboard is dismissed |
| **Sandboxed** | Cannot access host app data |
| **No microphone by default** | Must request "Allow Full Access" for mic |
| **Extension lifecycle** | May be terminated by system at any time |

## Key Components

### UIInputViewController

```swift
class TypelessKeyboardViewController: UIInputViewController {
    // Text insertion
    func insertText(_ text: String) {
        textDocumentProxy.insertText(text)
    }

    // Lifecycle
    override func viewDidLoad()
    override func viewWillAppear(_ animated: Bool)
    override func viewWillDisappear(_ animated: Bool)
}
```

### KMP Integration

The KMP shared module is integrated via a framework:

```swift
// Access KMP shared code from Swift
let viewModel = RealtimeViewModelHelper.create()
viewModel.connect(sourceLanguage: "hi-IN", targetLanguage: "en-IN")
```

### Audio Capture

```swift
// AVAudioEngine for low-latency audio capture
let audioEngine = AVAudioEngine()
let inputNode = audioEngine.inputNode
let format = inputNode.outputFormat(forBus: 0)

inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, time in
    // Convert to PCM bytes and send to KMP RealtimeRepository
}
```

### Permissions

- **Allow Full Access**: Required for network AND microphone in keyboard extension
- User must explicitly enable in Settings → Keyboards → Typeless → Allow Full Access
- The app must clearly explain why full access is needed

### State Handling

- Keyboard extension may be killed at any time by iOS
- WebSocket connections must handle abrupt termination gracefully
- State should be recoverable (reconnect on next keyboard appearance)

## Differences from Android

| Aspect | Android | iOS |
|---|---|---|
| **Keyboard service** | `InputMethodService` (background) | `UIInputViewController` (extension) |
| **Text insertion** | `InputConnection.commitText()` | `textDocumentProxy.insertText()` |
| **Microphone** | Direct permission | Requires "Allow Full Access" |
| **Network** | Always available | Requires "Allow Full Access" |
| **Memory limit** | Generous | ~50 MB |
| **Background** | Service continues | Extension may be killed |
| **Lifecycle** | Stable | Extension may restart |
