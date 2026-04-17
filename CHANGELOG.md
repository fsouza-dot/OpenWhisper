# Changelog

All notable changes to OpenWhisper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.5] - 2026-04-17

### Added
- Friendly error dialog when VC++ Redistributable is missing
- MSI installer checks for VC++ runtime before installation
- Version display in settings sidebar
- Windows security warning instructions in README

### Fixed
- Quick press-release no longer produces hallucinated text (minimum duration check)
- Silent recordings are now skipped (audio energy threshold)
- Paste compatibility with Notepad, Notepad++, and terminals

### Changed
- Removed auto-update system (will be redesigned later)

## [0.2.0] - 2026-04-15

### Added
- Windows 11 style Settings UI
- History window with correction learning
- Dictionary settings page
- Personal dictionary with aliases

## [0.1.0] - 2026-04-13

### Added
- Initial open source release
- Global push-to-talk hotkey (Alt+Space) with toggle mode option
- Two STT backends: local faster-whisper and Groq cloud
- Multilingual support (English + Portuguese)
- Minimal floating HUD with animated recording indicator
- System tray integration with settings access
- Microphone selector with test functionality
- Groq free-tier usage tracking
- Privacy-first design: audio in RAM only, keys in Credential Manager

### Notes
- Windows-only for now — Mac and Linux support planned
- Vibecoded in an afternoon with cross-platform architecture in mind
