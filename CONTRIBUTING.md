# Contributing to OpenWhisper

Thanks for your interest in OpenWhisper! This project was vibecoded in an afternoon and we're excited to grow it with the community. Contributions of all sizes are welcome — bug reports, docs, new features, or just feedback.

## We're Looking For Help With

**High-impact contributions we'd love to see:**

- **Mac support** — PySide6 and sounddevice work on Mac, but we need help with:
  - Global hotkey registration (pynput works differently on Mac)
  - Paste simulation (Cmd+V instead of Ctrl+V)
  - Testing and polish

- **Linux support** — Should mostly work, needs:
  - Testing on major distros (Ubuntu, Fedora, Arch)
  - Hotkey registration via pynput or alternatives
  - Clipboard/paste handling

- **New STT backends** — Implement `SpeechToTextProvider` in `openwhisper/protocols.py`:
  - AssemblyAI
  - Deepgram
  - Local Whisper.cpp
  - Azure Speech Services

- **UI improvements** — The HUD and settings window could always be better

- **Documentation** — Screenshots, tutorials, platform-specific guides

## Development Setup

Windows 10/11, Python 3.11+:

```powershell
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

For Mac/Linux development (partial support):
```bash
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Some features won't work yet — that's what we need help with!
```

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests are pure Python — no audio, no Qt, no network. They run fast and work on any platform.

## Code Style

- Python 3.11+, type hints on public functions
- Keep it simple — this was vibecoded in an afternoon, let's keep that energy
- Follow the layering: domain code can't import Qt/platform stuff
- No telemetry, no analytics, no tracking — ever

## Making Changes

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit with a clear message
6. Open a PR

For larger changes, open an issue first to discuss the approach.

## Platform-Specific Code

If you're adding Mac or Linux support, the key files are:

- `openwhisper/hotkey/hotkey_manager.py` — global hotkey registration
- `openwhisper/insertion/paste_inserter.py` — clipboard + paste simulation
- `openwhisper/audio/recorder.py` — should work cross-platform via sounddevice

The rest of the codebase is intentionally platform-agnostic.

## Questions?

Open an issue or start a discussion. We're friendly!

## Code of Conduct

Be kind, assume good faith, keep it technical. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
