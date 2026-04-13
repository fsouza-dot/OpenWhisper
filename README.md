# OpenWhisper

**A local-first, privacy-respecting dictation assistant.**
Hold a hotkey, speak, release — your text lands in whatever app you were using.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## The Story

OpenWhisper was **vibecoded in an afternoon** — built rapidly with AI assistance to prove that a polished, privacy-first dictation app doesn't need to be complicated or expensive. The goal was simple: create something that works beautifully on day one, with an architecture clean enough to expand to other platforms.

**Current status:** Windows-only, but since it's pure Python with cross-platform libraries (PySide6, sounddevice, pynput), **Mac and Linux support is coming soon**. The hard part is done — we just need to wire up platform-specific bits for audio input and hotkeys.

**We're actively looking for collaborators!** Whether you want to help bring OpenWhisper to Mac/Linux, add new STT backends, improve the UI, or just fix bugs — PRs are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## What It Does

OpenWhisper sits in your system tray. Press **Alt+Space**, speak, release — your words appear as text in whatever app you're using. No clicking, no separate window, no friction.

Built on [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (local) or Groq's hosted `whisper-large-v3-turbo` (cloud). Works in every app via clipboard + synthesized `Ctrl+V`.

## Features

- **Global push-to-talk hotkey** (default **Alt+Space**) — works in every app
- **Two STT backends** — local `faster-whisper` or Groq cloud (sub-second transcription)
- **Multilingual** — English + Portuguese out of the box, easy to add more
- **Minimal UI** — tiny floating indicator while recording, otherwise invisible
- **Privacy-first** — audio stays in RAM, API keys in system credential manager, zero telemetry

## Screenshots

> Coming soon — PRs welcome!

## Install

### Prerequisites

- Windows 10 or 11
- Python **3.11+**
- A working microphone

### From Source

```powershell
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### Prebuilt Executable

See [Releases](../../releases) for standalone `.exe` builds. No Python required.

## Quick Start

1. Launch OpenWhisper — look for the tray icon
2. Open **Settings** from the tray menu
3. (Recommended) Add a free [Groq API key](https://console.groq.com) for fast cloud transcription
4. Press **Alt+Space**, speak, release
5. Your text appears wherever your cursor was

## Platform Roadmap

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows** | Working | Full feature support |
| **macOS** | Planned | PySide6 + sounddevice work on Mac, need hotkey + paste fixes |
| **Linux** | Planned | Should work with minor tweaks, need testing |

The codebase is intentionally cross-platform. Most platform-specific code lives in:
- `openwhisper/hotkey/` — global hotkey registration
- `openwhisper/insertion/` — clipboard + paste simulation

PRs for Mac/Linux support are especially welcome!

## Configuration

| What | Where |
|------|-------|
| Settings | `%APPDATA%\OpenWhisper\settings.json` |
| Logs | `%APPDATA%\OpenWhisper\openwhisper.log` |
| API keys | Windows Credential Manager |

## Privacy

- **Audio stays in RAM** — never written to disk
- **Keys in Credential Manager** — not in config files
- **No telemetry** — zero analytics, zero tracking
- **You control the network** — only calls the STT providers you configure

## Architecture

Clean layered design — see [ARCHITECTURE.md](ARCHITECTURE.md):

```
UI (PySide6) → Coordinator (state machine) → Domain (pure Python) → Platform (audio, hotkey, STT)
```

Every integration is behind a Protocol, making it easy to swap STT backends, add new platforms, or change the insertion method.

## Contributing

We'd love your help! OpenWhisper is intentionally simple and hackable.

**Good first contributions:**
- Mac or Linux platform support
- New STT backend (AssemblyAI, Deepgram, local Whisper.cpp)
- UI improvements
- Documentation and examples
- Bug reports and fixes

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Building

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm OpenWhisper.spec
# Output: dist\OpenWhisper\OpenWhisper.exe
```

## License

MIT — see [LICENSE](LICENSE).

---

**Built with vibecoding and coffee.** If you find OpenWhisper useful, give it a star and tell a friend!
