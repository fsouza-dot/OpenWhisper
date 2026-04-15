# OpenWhisper on macOS

## Installation

### Download

Download the appropriate DMG for your Mac:

- **Apple Silicon (M1/M2/M3)**: `OpenWhisper-arm64.dmg`
- **Intel Mac**: `OpenWhisper-x86_64.dmg`

### Install

1. Open the DMG file
2. Drag **OpenWhisper** to the **Applications** folder
3. Eject the DMG
4. Launch OpenWhisper from Applications

## Required Permissions

OpenWhisper needs two system permissions to function properly:

### 1. Microphone Access

macOS will automatically prompt for microphone access when you first try to record. Click **OK** to allow.

If you denied access, you can enable it later:
1. Open **System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security** > **Microphone**
3. Find **OpenWhisper** and enable the toggle

### 2. Accessibility Access (for Global Hotkeys)

OpenWhisper needs accessibility access to register global hotkeys that work in any application.

1. Open **System Settings**
2. Go to **Privacy & Security** > **Accessibility**
3. Click the lock icon and enter your password
4. Click **+** and add **OpenWhisper** from Applications
5. Enable the toggle next to OpenWhisper

**Note**: You may need to restart OpenWhisper after granting accessibility access.

## Troubleshooting

### "OpenWhisper is damaged and can't be opened"

This message appears because the app is not signed with an Apple Developer certificate. To bypass:

**Option 1: Right-click to open**
1. Right-click (or Control-click) on OpenWhisper in Applications
2. Select **Open** from the context menu
3. Click **Open** in the dialog that appears

**Option 2: Remove quarantine attribute**
```bash
xattr -cr /Applications/OpenWhisper.app
```

### Hotkey doesn't work

1. Ensure accessibility permission is granted (see above)
2. Try restarting OpenWhisper
3. Check that your hotkey isn't conflicting with system shortcuts

### No menu bar icon

1. Check if your menu bar is full - some items may be hidden
2. Try using a tool like Bartender or Dozer to reveal hidden icons
3. Restart OpenWhisper

### Microphone not detected

1. Check System Settings > Privacy & Security > Microphone
2. Ensure OpenWhisper has permission
3. Try selecting a different input device in Settings

## Configuration

All settings are accessible from the menu bar icon:
1. Click the OpenWhisper icon in the menu bar
2. Select **Settings...**

Settings are saved to: `~/Library/Application Support/OpenWhisper/`

## Uninstall

1. Quit OpenWhisper from the menu bar
2. Delete OpenWhisper from Applications
3. (Optional) Remove settings:
   ```bash
   rm -rf ~/Library/Application\ Support/OpenWhisper
   ```

## Building from Source

### Prerequisites

- macOS 12+ (Monterey or later)
- Python 3.11+
- Homebrew

### Setup

```bash
# Install system dependencies
brew install portaudio

# Clone the repository
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m openwhisper
```

### Build .app Bundle

```bash
# Install PyInstaller
pip install pyinstaller

# Build
python -m PyInstaller --noconfirm OpenWhisper-macos.spec

# Output: dist/OpenWhisper.app
```

### Create DMG

```bash
mkdir -p dmg_staging
cp -r dist/OpenWhisper.app dmg_staging/
ln -s /Applications dmg_staging/Applications
hdiutil create -volname "OpenWhisper" -srcfolder dmg_staging -ov -format UDZO OpenWhisper.dmg
```

## Known Limitations

- **Unsigned app**: Requires manual bypass of Gatekeeper (see Troubleshooting)
- **Text insertion**: Works best in standard text fields; some apps may require accessibility permission
- **Local Whisper**: Downloads models on first use (~1-3GB depending on model size)
