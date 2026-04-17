# Claude Code Instructions for OpenWhisper

## Project Overview
OpenWhisper is a local-first dictation assistant for Windows that uses Whisper for speech-to-text.

## Three Workflows

### 1. Dev Build (for testing)
When user asks to "build", "test build", or "run the app":
- Build executable only using PyInstaller (no MSI)
- Use the virtual environment: `.venv/Scripts/python.exe -m PyInstaller`
- Output to `dist/OpenWhisper/`
- Do NOT commit, push, or create releases
- Do NOT build MSI or ZIP

```bash
.venv/Scripts/python.exe -m PyInstaller --noconfirm openwhisper.spec
```

### 2. Commit (code only)
When user asks to "commit" or "push to GitHub":
- Stage and commit the code changes
- Push to GitHub if requested
- Do NOT build anything
- Do NOT create releases or upload files

### 3. Release (full process)
When user asks to "release", "publish", or "create a release":
1. **Update version numbers** in all locations:
   - `openwhisper/__init__.py`
   - `pyproject.toml`
   - `OpenWhisper.wxs`
2. **Update CHANGELOG.md** with release notes
3. **Commit** all changes with version in commit message
4. **Build everything**:
   - PyInstaller executable
   - ZIP file: `OpenWhisper-{version}-win64.zip`
   - MSI installer: `OpenWhisper-{version}-win64.msi`
5. **Ask for confirmation** before pushing and publishing
6. **Push** to GitHub
7. **Create GitHub release** with ZIP and MSI attached

## GitHub Publishing - REQUIRES CONFIRMATION
**IMPORTANT**: Never publish anything to GitHub without explicit user confirmation:
- Creating releases (`gh release create`)
- Uploading release assets (`gh release upload`)
- Pushing to remote branches (`git push`)
- Creating pull requests (`gh pr create`)

Before executing any of these actions, always ask:
> "Ready to publish to GitHub. Should I proceed with [action description]?"

Wait for explicit confirmation (e.g., "yes", "go ahead", "do it") before proceeding.

## Build Commands

### Dev build (executable only)
```bash
.venv/Scripts/python.exe -m PyInstaller --noconfirm openwhisper.spec
```

### Create ZIP
```bash
cd dist && powershell -Command "Compress-Archive -Path 'OpenWhisper' -DestinationPath 'OpenWhisper-{version}-win64.zip' -Force"
```

### Create MSI
```bash
wix build -o dist/OpenWhisper-{version}-win64.msi OpenWhisper.wxs
```

## Tech Stack
- Python 3.11+
- PySide6 for UI
- faster-whisper for local STT
- Groq API for cloud STT
- PyInstaller for packaging
- WiX Toolset for MSI installers

## Testing
- Run `python -m pytest tests/` before committing
- Test the built executable manually when possible
- Verify the app starts correctly after changes
