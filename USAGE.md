# Using OpenWhisper

## First Launch

1. Run `OpenWhisper.exe` or `python run.py`
2. Look for the microphone icon in your system tray (bottom-right of your screen)
3. Right-click the tray icon and select **Settings**

## Setting Up

### Choose Your STT Backend

OpenWhisper supports two speech-to-text backends:

| Backend | Speed | Privacy | Setup |
|---------|-------|---------|-------|
| **Groq Cloud** | Fast (~1 second) | Audio sent to Groq API | Requires free API key |
| **Local Whisper** | Slower (~3-5 seconds) | 100% offline | No setup needed |

### Getting a Groq API Key (Recommended)

1. Go to [console.groq.com](https://console.groq.com)
2. Create a free account
3. Generate an API key
4. Paste it in OpenWhisper Settings > STT tab

Groq's free tier is generous for personal use.

### Selecting Your Microphone

1. Open Settings > Audio tab
2. Select your preferred microphone from the dropdown
3. Click **Test Mic** to verify it's working

## Basic Usage

### Push-to-Talk (Default)

1. Click where you want your text to appear
2. Press and **hold** `Alt+Space`
3. Speak clearly
4. Release the hotkey
5. Your text appears at the cursor

### Toggle Mode

If you prefer tap-to-start, tap-to-stop:

1. Open Settings > Hotkey tab
2. Enable **Toggle Mode**
3. Now: tap once to start recording, tap again to stop

## The HUD

When recording, a small floating indicator appears showing three animated dots. This tells you OpenWhisper is listening.

| State | What You See |
|-------|--------------|
| Recording | Three bouncing dots |
| Transcribing | Single pulsing dot |
| Error | Red flash |

## Languages

OpenWhisper supports multiple languages. Change the language in Settings > General tab.

Currently supported:
- English
- Portuguese

The Whisper model auto-detects language, but setting it explicitly can improve accuracy.

## Dictation Modes

| Mode | Best For | Example |
|------|----------|---------|
| **Prose** | Emails, documents | Full sentences with punctuation |
| **Code** | Programming | Minimal formatting changes |
| **Raw** | Maximum accuracy | Exactly what you said |

## Tips

- **Speak naturally** — Whisper handles conversational speech well
- **Pause briefly** before speaking if using toggle mode
- **Check the tray icon** — it shows current status
- **Use Groq** for fastest results — local Whisper is slower but fully offline

## Troubleshooting

### Nothing happens when I press the hotkey

- Make sure OpenWhisper is running (check system tray)
- Try running as Administrator
- Check if another app is capturing `Alt+Space`

### Transcription is slow

- Switch to Groq backend for ~1 second transcriptions
- Local Whisper takes 3-5 seconds depending on your CPU

### Text appears in wrong place

- OpenWhisper uses clipboard + Ctrl+V
- Make sure your cursor is focused where you want text
- Some apps may block paste — try a different app

### Microphone not detected

- Check Windows sound settings
- Make sure your mic isn't muted
- Try selecting a different device in Settings

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt+Space` | Push-to-talk (hold) or toggle recording |

The hotkey can be customized in Settings > Hotkey tab.
