# Building OpenWhisper

## Prerequisites

- Windows 10 or 11
- Python 3.11 or higher
- Git

## Development Setup

### 1. Clone the Repository

```powershell
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper
```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run from Source

```powershell
python run.py
```

## Building the Executable

We use PyInstaller to create a standalone Windows executable.

### Build Command

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm OpenWhisper.spec
```

### Output

The built application will be in:
```
dist\OpenWhisper\OpenWhisper.exe
```

### What's Included

The PyInstaller spec bundles:
- All Python dependencies
- PySide6 (Qt) runtime
- faster-whisper model loading code
- Application icons and assets

## Project Structure

```
OpenWhisper/
├── run.py                 # Entry point
├── OpenWhisper.spec       # PyInstaller configuration
├── requirements.txt       # Python dependencies
├── openwhisper/
│   ├── app.py            # Application composition root
│   ├── coordinator.py    # State machine
│   ├── protocols.py      # Interface definitions
│   ├── settings.py       # Configuration management
│   ├── audio/            # Audio recording
│   ├── stt/              # Speech-to-text backends
│   ├── hotkey/           # Global hotkey handling
│   ├── insertion/        # Text insertion (clipboard)
│   ├── cleanup/          # Text post-processing
│   └── ui/               # PySide6 user interface
└── assets/               # Icons and images
```

## Development Notes

### Running Tests

```powershell
pytest
```

### Code Style

The project doesn't enforce strict linting, but try to:
- Keep functions focused and small
- Use type hints where helpful
- Follow existing patterns in the codebase

### Hot Reload

There's no hot reload — restart the app after code changes.

### Debugging

Logs are written to:
```
%APPDATA%\OpenWhisper\openwhisper.log
```

To see logs in real-time while developing:
```powershell
Get-Content "$env:APPDATA\OpenWhisper\openwhisper.log" -Wait
```

## Platform-Specific Code

Most of the codebase is cross-platform Python. Platform-specific bits live in:

| Directory | Purpose | Platform Status |
|-----------|---------|-----------------|
| `openwhisper/hotkey/` | Global hotkey registration | Windows only |
| `openwhisper/insertion/` | Clipboard + paste simulation | Windows only |

If you're adding Mac or Linux support, these are the main areas to focus on.

## Dependencies

Key dependencies:
- **PySide6** — Qt bindings for the UI
- **sounddevice** — Audio recording
- **faster-whisper** — Local Whisper inference
- **groq** — Groq API client
- **pynput** — Global hotkey capture
- **keyring** — Secure credential storage

See `requirements.txt` for the full list.

## Troubleshooting Builds

### PyInstaller can't find modules

Make sure you're running PyInstaller from the activated virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm OpenWhisper.spec
```

### Build is huge

The faster-whisper dependency pulls in large ML libraries. This is expected. A typical build is 500MB-1GB.

### App crashes on startup after build

Check the console output or logs. Common issues:
- Missing DLLs — try rebuilding with a fresh venv
- Path issues — make sure assets are bundled correctly in the spec file
