# Changelog

All notable changes to OpenWhisper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **macOS support** (Apple Silicon). Native `.app` bundle distributed as
  `OpenWhisper-arm64.dmg`. Keyboard injection uses Quartz CGEvent for
  reliable paste in browsers and Electron apps. Launch-at-login via
  LaunchAgents. First-launch Accessibility permission prompt. See
  [MACOS.md](MACOS.md).

## [0.3.5] - 2026-04-17

### Initial Release

OpenWhisper is a local-first, privacy-respecting dictation assistant for Windows.

### Features
- **Push-to-talk dictation** - Hold Alt+Space, speak, release to insert text
- **Toggle mode** - Alternative to push-to-talk for longer dictations
- **Two STT backends** - Local faster-whisper or Groq cloud API
- **Multilingual support** - 90+ languages supported
- **Windows 11 style Settings UI** - Modern, clean interface
- **History window** - Review and learn from past dictations
- **Personal dictionary** - Custom word replacements and aliases
- **Microphone selector** - Choose and test your input device
- **System tray integration** - Runs quietly in the background
- **Floating HUD** - Minimal recording indicator
- **Groq usage tracking** - Monitor your free-tier API usage

### Privacy & Security
- Audio stays in RAM only - never written to disk
- API keys stored in Windows Credential Manager
- No telemetry or data collection

### Compatibility
- Works with Notepad, Notepad++, terminals, and other applications
- Requires Microsoft Visual C++ Redistributable (installer checks automatically)

### Notes
- Initial release: Windows 10/11. macOS and Linux support arrived in subsequent releases.
