# Claude Code Instructions for OpenWhisper

## Project Overview
OpenWhisper is a local-first dictation assistant for Windows that uses Whisper for speech-to-text.

## Build and Release Rules

### GitHub Publishing - REQUIRES CONFIRMATION
**IMPORTANT**: Never publish anything to GitHub without explicit user confirmation. This includes:
- Creating releases (`gh release create`)
- Uploading release assets (`gh release upload`)
- Pushing to remote branches (`git push`)
- Creating pull requests (`gh pr create`)
- Creating issues or comments

Before executing any of these actions, always ask:
> "Ready to publish to GitHub. Should I proceed with [action description]?"

Wait for explicit confirmation (e.g., "yes", "go ahead", "do it") before proceeding.

### Build Outputs
When building executables or installers:
1. Build the application with PyInstaller
2. Create ZIP and MSI installers
3. **Ask for confirmation** before uploading to GitHub releases

## Development Guidelines

### Version Updates
When releasing a new version:
1. Update version in `openwhisper/__init__.py`
2. Update version in `pyproject.toml`
3. Update version in `OpenWhisper.wxs` (for MSI)
4. Commit changes
5. **Ask for confirmation** before pushing and creating release

### Testing
- Run `python -m pytest tests/` before committing
- Test the built executable manually when possible
- Verify the app starts correctly after changes

## Tech Stack
- Python 3.11+
- PySide6 for UI
- faster-whisper for local STT
- Groq API for cloud STT
- PyInstaller for packaging
- WiX for MSI installers
