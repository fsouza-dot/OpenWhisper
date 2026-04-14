# OpenWhisper on Linux

## Quick Start (from source)

### 1. Install system dependencies

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install python3-dev python3-venv portaudio19-dev \
    libxcb-xinerama0 libxcb-cursor0 libsecret-1-dev xdotool
```

**Fedora:**
```bash
sudo dnf install python3-devel portaudio-devel libxcb libsecret-devel xdotool
```

**Arch:**
```bash
sudo pacman -S python portaudio libsecret xdotool
```

### 2. Clone and setup

```bash
git clone https://github.com/fsouza-dot/OpenWhisper.git
cd OpenWhisper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run

```bash
python run.py
```

### 4. Configure

- Look for the OpenWhisper icon in your system tray
- Right-click and select **Settings**
- Add your Groq API key (get one free at https://console.groq.com)
- Select your languages

### 5. Use

Press **Alt+Space**, speak, release. Your text appears wherever your cursor was.

---

## Building a Standalone Executable

```bash
chmod +x build-linux.sh
./build-linux.sh
```

Output will be in `dist/OpenWhisper/`.

To distribute:
```bash
cd dist
tar -czvf OpenWhisper-linux.tar.gz OpenWhisper/
```

---

## Troubleshooting

### Hotkey doesn't work on Wayland

pynput has limited Wayland support. Try running in X11 mode:
```bash
GDK_BACKEND=x11 python run.py
```

Or install and use XWayland.

### No system tray icon

Some desktop environments hide tray icons by default. Install a tray extension:
- GNOME: Install "AppIndicator and KStatusNotifierItem Support" extension
- KDE: Should work out of the box

### Keyring errors

If you see keyring errors, install the SecretService backend:
```bash
sudo apt install gnome-keyring  # or
sudo apt install kwalletmanager
```

### Audio not working

Check that PortAudio can see your microphone:
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

---

## Known Limitations

- Wayland support is partial (X11 recommended)
- Some desktop environments may block global hotkeys
- Tested on: Ubuntu 22.04+, Fedora 38+, Arch Linux
