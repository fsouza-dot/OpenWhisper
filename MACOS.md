# OpenWhisper on macOS

OpenWhisper supports Apple Silicon Macs (M1 and later) running macOS 12 or
newer. Intel Macs are not currently supported.

## Install

1. Download `OpenWhisper-arm64.dmg` from
   [Releases](https://github.com/fsouza-dot/OpenWhisper/releases).
2. Open the DMG and drag **OpenWhisper** to **Applications**.
3. Because the app is not signed with an Apple Developer certificate,
   macOS Gatekeeper will quarantine it. Remove the quarantine flag once:
   ```bash
   xattr -cr /Applications/OpenWhisper.app
   ```
   Alternatively, the first time you launch the app, right-click it in
   Applications and choose **Open**, then click **Open** in the dialog.
4. Launch **OpenWhisper** from Applications. The icon appears in the
   menu bar (top-right of the screen). The app deliberately does not
   show in the Dock.

## Permissions

OpenWhisper needs two macOS permissions to function. The first time you
launch the app it asks for both.

### Microphone

Triggered automatically by macOS the first time you start a recording.
If you previously denied it:

1. Open **System Settings → Privacy & Security → Microphone**.
2. Enable **OpenWhisper**.

### Accessibility

Required so the app can register a global hotkey and paste transcribed
text into the focused application. OpenWhisper presents the system
prompt on first launch:

1. Open **System Settings → Privacy & Security → Accessibility**.
2. Enable **OpenWhisper**.
3. Quit and relaunch OpenWhisper for the change to take effect.

If hotkeys appear to do nothing, this permission is the first thing to
check.

## Where files live

| Item | Location |
|------|----------|
| Settings | `~/Library/Application Support/OpenWhisper/settings.json` |
| Logs | `~/Library/Application Support/OpenWhisper/openwhisper.log` |
| Whisper models | `~/Library/Application Support/OpenWhisper/models/` |
| API keys | macOS Keychain (service: `OpenWhisper`) |
| Launch-at-login agent | `~/Library/LaunchAgents/com.openwhisper.app.plist` |

## Troubleshooting

**"OpenWhisper is damaged and can't be opened"** — Gatekeeper quarantine.
Run `xattr -cr /Applications/OpenWhisper.app`.

**Hotkey does nothing** — Accessibility permission missing or app needs
restart after granting it. Re-check System Settings → Privacy & Security
→ Accessibility.

**No menu bar icon** — Your menu bar may be full. Tools like Bartender
or Ice can reveal hidden icons. The app intentionally has no Dock icon.

**Microphone not detected** — Check System Settings → Privacy & Security
→ Microphone. If the input device list is empty in OpenWhisper Settings,
make sure your input device is connected and visible in System Settings
→ Sound → Input.

## Build from source

Requires macOS 12+ on an Apple Silicon Mac, Homebrew, and Python 3.11+.

```bash
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper
./build-macos.sh
```

The script installs portaudio via Homebrew, sets up a virtualenv,
installs dependencies, generates the icon, runs PyInstaller, and
packages the result as `OpenWhisper-arm64.dmg`.

## Uninstall

1. Quit OpenWhisper from the menu bar.
2. Delete `/Applications/OpenWhisper.app`.
3. Disable launch-at-login (if enabled): `rm ~/Library/LaunchAgents/com.openwhisper.app.plist`.
4. Remove user data: `rm -rf ~/Library/Application\ Support/OpenWhisper`.
5. Remove the Keychain entry from **Keychain Access** (search for
   `OpenWhisper`) if you stored a Groq API key.
