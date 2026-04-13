# OpenWhisper Architecture (Windows)

## Goals

1. **Feel instant.** Sub-second finalization on the cloud path; <3 s on the local path for a typical 5 s clip.
2. **Work in any app.** No per-app integration. Clipboard + synthesized Ctrl+V is the universal insertion channel.
3. **Degrade gracefully.** No Groq key? Use local whisper. No Anthropic key? Skip Claude and use local heuristic cleanup. No network? Local path still works end to end.
4. **Privacy by construction.** Audio never touches disk. API keys live in Windows Credential Manager, not `settings.json`.
5. **Swappable layers.** Every integration is behind a protocol in `protocols.py`. STT backends, LLM cleanup, text insertion — all pluggable.

## Layering

```
┌─────────────────────────────────────────────────────────┐
│  UI layer (PySide6 / Qt)                                │
│  TrayIcon · HUDWindow · SettingsWindow · OnboardingDialog│
└─────────────────────────────────────────────────────────┘
                     │  (Qt signals, UIState)
┌─────────────────────────────────────────────────────────┐
│  Coordinator (state machine)                            │
│  idle → recording → transcribing → cleaning → inserting │
└─────────────────────────────────────────────────────────┘
                     │  (protocol calls)
┌─────────────────────────────────────────────────────────┐
│  Domain layer (pure Python, no Qt / no win32)           │
│  cleanup pipeline · command interpreter · dictionary ·  │
│  snippet expander · heuristic cleanup · history         │
└─────────────────────────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────┐
│  Integrations                                           │
│  audio (sounddevice) · stt (faster-whisper, groq) ·     │
│  insertion (SendInput) · hotkey (pynput) ·              │
│  secrets (keyring) · cleanup.claude (anthropic SDK)     │
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
├── keyring_store.py    Credential Manager wrapper (Anthropic + Groq)
├── logging_setup.py    Rotating file logger
├── history.py          Recent dictations (for undo_last_dictation)
│
├── audio/recorder.py   sounddevice InputStream, 16 kHz mono Float32
├── stt/
│   ├── whisper_provider.py   Local faster-whisper (CTranslate2)
│   └── groq_provider.py      Cloud Groq /audio/transcriptions
├── cleanup/
│   ├── pipeline.py     Orchestrates dictionary → snippets → heuristic → LLM
│   ├── dictionary.py   Personal dictionary
│   ├── snippets.py     Snippet expansion
│   ├── heuristic.py    Regex/rules cleanup (no LLM)
│   └── claude_provider.py    Anthropic SDK, Haiku 4.5 with prompt caching
├── commands/
│   ├── command.py      DictationCommand enum
│   └── interpreter.py  Regex command fast-path
├── hotkey/hotkey_manager.py  pynput global listener (PTT + toggle)
├── insertion/paste_inserter.py  Clipboard + Windows SendInput Ctrl+V
└── ui/
    ├── tray.py         System tray icon
    ├── hud.py          Minimal 56×56 status pill
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
└──────────┘                 └────────────────┘         └────┬──────┘
                                     │ text                  │
                                     ▼                       │
                             ┌───────────────┐               │
                             │ Cleanup       │ ◀─────────────┘
                             │ dict→snip→heur│
                             │ →Claude?      │
                             └───────┬───────┘
                                     │ cleaned text + optional command
                                     ▼
                             ┌───────────────┐
                             │  Inserter     │
                             │  clipboard +  │
                             │  SendInput ^V │
                             └───────────────┘
```

All heavy work (STT + Claude) runs on a background thread spawned by the
coordinator. The Qt event loop is never blocked. Phase transitions are
published to the UI via Qt signals — background threads emit through an
intermediary signal that's handled on the Qt thread.

## Threading model

- **Qt main thread** — owns every widget and timer. Handles UI events.
- **Audio callback thread** — `sounddevice` InputStream callback; only appends to a lock-protected chunk list.
- **Pipeline worker thread** — spawned by the coordinator on `PTT up`. Runs STT + cleanup + insertion serially. Uses `_phase_signal`, `_preview_signal`, `_inserted_signal`, and `_schedule_idle_signal` to talk back to the Qt thread.
- **Warmup thread** — launched at app start to preload the local whisper model so the first hotkey press doesn't eat the ~2–5 s model-load cost.

## State machine

`coordinator.DictationCoordinator` owns the phase. `Phase` values: `idle`, `recording`, `transcribing`, `cleaning`, `inserting`, `error`. Transitions:

- `idle → recording` — on PTT down / toggle first tap.
- `recording → transcribing` — on PTT up / toggle second tap.
- `transcribing → cleaning` — after whisper returns non-empty text.
- `cleaning → inserting` — after the cleanup pipeline returns cleaned text.
- `inserting → idle` — after SendInput completes (auto-idle via `_schedule_idle_signal`).
- `* → error → idle` — on any exception in STT/cleanup/insertion, with a 1.5 s hold so the user sees the HUD flash orange.

## Performance notes

- **Local whisper** runs in **CPU int8** mode. `device="auto"` is overridden to `"cpu"` because CTranslate2 tries to load CUDA at encode time and the PyInstaller build does not ship cuBLAS.
- **Transcribe flags** are tuned for push-to-talk dictation: `beam_size=1`, `vad_filter=False`, `without_timestamps=True`, `condition_on_previous_text=False`. Collectively ~2–3× faster than defaults.
- **Model warmup** happens on app start on a background thread.
- **Groq backend** is the latency win when offline isn't required. It encodes Float32 → 16-bit PCM WAV with stdlib `wave`, posts multipart to `https://api.groq.com/openai/v1/audio/transcriptions`, and requests `response_format=text` to skip JSON overhead.
- **Claude cleanup** uses ephemeral prompt caching on the system prompt so the ~1 KB ruleset is 90%-discounted after the first call.
- **Paste path** uses raw Windows `SendInput` via ctypes (40-byte INPUT struct sized for the 64-bit MOUSEINPUT variant) and force-releases Alt/Ctrl/Shift/Win before firing Ctrl+V — otherwise pynput's stale modifier tracking can turn the paste into Ctrl+Alt+V after an Alt+Space hotkey.

## Data locations

- **Settings**: `%APPDATA%\OpenWhisper\settings.json`
- **Log**: `%APPDATA%\OpenWhisper\openwhisper.log`
- **Whisper model cache**: `%USERPROFILE%\.cache\huggingface\`
- **Secrets**: Windows Credential Manager under service `OpenWhisper`, accounts `anthropic_api_key` and `groq_api_key`.

## Extension points

- **New STT backend**: implement the `SpeechToTextProvider` protocol (`transcribe(AudioBuffer, List[str]) -> Transcript`), add it to `STTProviderKind`, wire it in `app._build_dynamic_services`.
- **New LLM cleanup backend**: implement `TextCleanupProvider.clean(CleanupInput) -> CleanupResult`. The cleanup pipeline treats it as interchangeable with Claude.
- **New insertion strategy**: implement `TextInsertionProvider.insert(str)`. Candidates: UI Automation direct-text insertion, IME composition string.
- **New language**: add the ISO 639-1 code to the Settings UI and `settings.languages`. The whisper provider will auto-switch to the multilingual model if any non-`en` language is present.
