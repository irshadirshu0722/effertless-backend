---
name: android-debugging
description: Runbook and guidelines for Android build, ADB automation, emulator inspection, Logcat analysis, and Chucker network tracing.
---

# Android Debugging & Inspection Runbook

This skill guides AI agents and engineers in debugging the Effortless Android application.

---

## 1. Prerequisites & Environment

Verify that the local environment has the Android SDK and platform tools configured:

```bash
# Check ADB availability
which adb
adb devices

# Check Android SDK path
echo $ANDROID_HOME # or ~/Library/Android/sdk on macOS
```

---

## 2. Core Build & Run Workflow

### A. Build the Debug APK

```bash
cd client
./gradlew :androidApp:assembleDebug
```

The output APK is generated at:
`client/androidApp/build/outputs/apk/debug/androidApp-debug.apk`

### B. Install on Emulator or Connected Device

```bash
adb install -r client/androidApp/build/outputs/apk/debug/androidApp-debug.apk
```

### C. Launch the Application

```bash
adb shell am start -n com.effortless.app/.MainActivity
```

---

## 3. Logcat Inspection

Filter Logcat to capture Effortless application events and Ktor network requests:

```bash
# Stream app logs with PID filtering
adb logcat --pid=$(adb shell pidof -s com.effortless.app)

# Stream only Ktor client and App tags
adb logcat -s KtorClient:D Effortless:D AndroidRuntime:E
```

---

## 4. UI Hierarchy & Screen Capture

### Take a Screenshot for UI Debugging

```bash
adb exec-out screencap -p > /tmp/effortless_screen.png
```

### Dump UI Hierarchy XML

```bash
adb shell uiautomator dump /data/local/tmp/uidump.xml
adb pull /data/local/tmp/uidump.xml /tmp/uidump.xml
```

---

## 5. Network Debugging with Chucker

Effortless integrates **Chucker** in debug builds to record and inspect HTTP requests/responses in realtime.

### Key Behaviors:
- **Active in Debug**: Inspects every HTTP request made by Ktor (OkHttp engine).
- **Zero-overhead in Release**: Backed by `library-no-op` in release builds.
- **Redacted Headers**: Automatically redacts `Authorization`, `X-API-Key`, `Cookie`, and `Set-Cookie`.
- **Viewing Chucker**:
  - A persistent notification is displayed on the device/emulator whenever HTTP traffic occurs.
  - Tapping the notification opens the Chucker activity (`com.chuckerteam.chucker.api.Chucker`).
  - You can launch Chucker directly via ADB:
    ```bash
    adb shell am start -n com.effortless.app/com.chuckerteam.chucker.api.ChuckerActivity
    ```

---

## 6. Common ADB Commands Reference

| Action | Command |
|---|---|
| **List Devices** | `adb devices -l` |
| **Clear App Data** | `adb shell pm clear com.effortless.app` |
| **Uninstall App** | `adb uninstall com.effortless.app` |
| **Grant Microphone Permission** | `adb shell pm grant com.effortless.app android.permission.RECORD_AUDIO` |
| **Send Text Input** | `adb shell input text "Hello%sWorld"` |
| **Press Back Button** | `adb shell input keyevent 4` |
| **Press Home Button** | `adb shell input keyevent 3` |
