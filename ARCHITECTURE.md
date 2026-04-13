# OpenWhisper Architecture (Windows)

## Goals

1. **Feel instant.** Sub-second finalization on the cloud path; <3 s on the local path for a typical 5 s clip.
2. **Work in any app.** No per-app integration. Clipboard + synthesized Ctrl+V is the universal insertion channel.
3. **Degrade gracefully.** No Groq key? Use local whisper. No network? Local path still works end to end.
4. **Privacy by construction.** Audio never touches disk. API keys live in Windows Credential Manager, not `settings.json`.
5. **Swappable layers.** Every integration is behind a protocol in `protocols.py`. STT backends, text insertion — all pluggable.

## Layering

```
┌─────────────────────────────────────────────────────────┐
│  UI layer (PySide6 / Qt)                                │
│  TrayIcon · HUDWindow · SettingsWindow · OnboardingDialog│
└─────────────────────────────────────────────────────────┘
                     │  (Qt signals, UIState)
┌─────────────────────────────────────────────────────────┐
│  Coordinator (state machine)                            │
│  idle → recording → transcribing → inserting            │
└─────────────────────────────────────────────────────────┘
                     │  (protocol calls)
┌─────────────────────────────────────────────────────────┐
│  Domain layer (pure Python, no Qt / no win32)           │
│  text processing · command interpreter · history        │
└─────────────────────────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────┐
│  Integrations                                           │
│  audio (sounddevice) · stt (faster-whisper, groq) ·     │
│  insertion (SendInput) · hotkey (pynput) ·              │
│  secrets (keyring)                                      │
└─────────────────────────────────────────────────────────┘
```

## Module map

```
openwhisper/
├── app.py              Composition root: wires every service and Qt
├── coordinator.py      State machine + background worker thread
├── protocols.py        Protocol classes so everything is swappable
├── settings.py         Pydantic AppSettings + JSON store
├── config.py           Filesystem paths, keyring constants
├── errors.py           Typed exceptions
├── keyring_store.py    Credential Manager wrapper
├── logging_setup.py    Rotating file logger
├── history.py          Recent dictations (for undo_last_dictation)
│
├── audio/recorder.py   sounddevice InputStream, 16 kHz mono Float32
├── stt/
│   ├── whisper_provider.py   Local faster-whisper (CTranslate2)
│   └── groq_provider.py      Cloud Groq /audio/transcriptions
├── cleanup/
│   ├── pipeline.py     Orchestrates text processing
│   └── heuristic.py    Regex/rules text processing
├── commands/
│   ├── command.py      DictationCommand enum
│   └── interpreter.py  Regex command fast-path
├── hotkey/hotkey_manager.py  pynput global listener (PTT + toggle)
├── insertion/paste_inserter.py  Clipboard + Windows SendInput Ctrl+V
└── ui/
    ├── tray.py         System tray icon
    ├── hud.py          Minimal animated status indicator
    ├── settings_window.py  Tabbed settings dialog
    ├── onboarding.py   First-run dialog
    └── ui_state.py     Shared phase/preview state, Qt signals
```

## Pipeline — per hotkey press

```
  PTT down                            PTT up
     │                                   │
     ▼                                   ▼
┌──────────┐  audio chunks   ┌────────────────┐   WAV   ┌───────────┐
│ Recorder │ ──────────────▶ │  Coordinator   │ ──────▶ │ STT       │
│ 16k mono │                 │  (worker thr.) │         │ Groq/local│
└──────────┘                 └────────────────┘         └───────────┘
                                     │ text
                                     ▼
                             ┌───────────────┐
                             │  Inserter     │
                             │  clipboard +  │
                             │  SendInput ^V │
                             └───────────────┘
```

All heavy work (STT) runs on a background thread spawned by the
coordinator. The Qt event loop is never blocked. Phase transitions are
published to the UI via Qt signals.

## Threading model

- **Qt main thread** — owns every widget and timer. Handles UI events.
- **Audio callback thread** — `sounddevice` InputStream callback; only appends to a lock-protected chunk list.
- **Pipeline worker thread** — spawned by the coordinator on `PTT up`. Runs STT + insertion serially.
- **Warmup thread** — launched at app start to preload the local whisper model so the first hotkey press doesn't eat the ~2–5 s model-load cost.

## State machine

`coordinator.DictationCoordinator` owns the phase. `Phase` values: `idle`, `recording`, `transcribing`, `inserting`, `error`. Transitions:

- `idle → recording` — on PTT down / toggle first tap.
- `recording → transcribing` — on PTT up / toggle second tap.
- `transcribing → inserting` — after whisper returns non-empty text.
- `inserting → idle` — after SendInput completes.
- `* → error → idle` — on any exception, with a 1.5 s hold so the user sees the HUD flash.

## Performance notes

- **Local whisper** runs in **CPU int8** mode.
- **Transcribe flags** are tuned for push-to-talk: `beam_size=1`, `vad_filter=False`, `without_timestamps=True`.
- **Model warmup** happens on app start on a background thread.
- **Groq backend** is the latency win — sub-second transcription.
- **Paste path** uses raw Windows `SendInput` via ctypes.

## Data locations

- **Settings**: `%APPDATA%\OpenWhisper\settings.json`
- **Log**: `%APPDATA%\OpenWhisper\openwhisper.log`
- **Whisper model cache**: `%USERPROFILE%\.cache\huggingface\`
- **Secrets**: Windows Credential Manager under service `OpenWhisper`.

## Extension points

- **New STT backend**: implement the `SpeechToTextProvider` protocol, add it to `STTProviderKind`, wire it in `app._build_dynamic_services`.
- **New insertion strategy**: implement `TextInsertionProvider.insert(str)`.
- **New language**: add the ISO 639-1 code to the Settings UI and `settings.languages`.
