# AquaBox Alerts Display System

A fullscreen alerts dashboard for Raspberry Pi 4 with 5-inch HDMI display, built for **Fluxgen Sustainable Technologies**.

Real-time water management alerts with multi-language TTS, AI chat assistant, and on-screen keyboard.

## Features

### Login & Security
- **Admin settings** — fullscreen with dark blue wave animation
- **API credentials** configured via admin page (`admin` / `admin`)
- User login validates against admin-configured credentials
- Session persistence (auto-login on reboot)
- **Built-in GTK on-screen keyboard** with numbers, @, !, #, $, shift toggle
- **Password eye icon** inside field to show/hide password
- Logout stops announcements immediately and clears all timers
- Animated login page with Fluxgen logo and water effects

### Alerts Dashboard
- **Read / Unread sections** with clickable stat boxes
- **Color-coded cards** by importance (high=red, medium=yellow, low=blue)
- **Auto-refresh** every 2 minutes with live countdown
- **Immediate retry** on fetch failure — refreshes token and retries up to 3 times
- **Network-ready wait** at boot — retries with backoff for 5 attempts
- **Mark as Read** via API with instant counter updates
- **WiFi manager** — scan, connect, and change WiFi from the alerts page
- **Volume control** via speaker icon

### Multi-Language TTS (6 Languages)
| Language | Code | Stable Flow | Filled | Upper Limit |
|----------|------|-------------|--------|-------------|
| English | ENG | Stable flow pattern detected | filled | Stock Level Upper limit reached |
| Telugu | TEL | స్థిరమైన ప్రవాహ నమూనా గుర్తించబడింది | నిండింది | నీటి మట్టం పై పరిమితి చేరుకుంది |
| Kannada | KAN | ಸ್ಥಿರ ಹರಿವಿನ ಮಾದರಿ ಪತ್ತೆಯಾಗಿದೆ | ತುಂಬಿದೆ | ನೀರಿನ ಮಟ್ಟ ಮೇಲಿನ ಮಿತಿ ತಲುಪಿದೆ |
| Tamil | TAM | நிலையான நீரோட்ட முறை கண்டறியப்பட்டது | நிரம்பியது | நீர் மட்டம் மேல் வரம்பை எட்டியது |
| Hindi | HIN | स्थिर प्रवाह पैटर्न पाया गया | भरा हुआ | जल स्तर ऊपरी सीमा पर पहुंच गया |
| Malayalam | MAL | സ്ഥിരമായ പ്രവാഹ രീതി കണ്ടെത്തി | നിറഞ്ഞു | ജല നിരപ്പ് ഉയർന്ന പരിധി എത്തി |

**TTS Improvements:**
- "L" reads as "liters", "kL" reads as "kiloliters"
- Stable flow pattern alerts properly translated in all languages
- No level variation alerts translated in all languages
- espeak fallback when internet is unavailable (with 44100Hz conversion)

### Announcements
- **Smart auto-announce** — only NEW unread alerts (tracks IDs via file)
- **Announce All** — generates and plays each alert instantly (no batch delay)
- **Announce Offline** — auto-announces every 3 hours
- **No overlapping audio** — all buttons guarded by `_auto_announcing` flag
- **Queue-based refresh** — refresh waits during announce
- **Dynamic typing speed** synced with audio duration
- **Cancel button** stops instantly, kills audio, resets all buttons
- **Thread-safe** — try/finally ensures `_auto_announcing` always resets

### WiFi Manager
- Tap **WiFi icon** (bottom-left) to open WiFi panel
- **Scan** for available networks with signal strength bars
- **Connect** to any network with password entry
- **Built-in GTK keyboard** for password input (panel moves to top when keyboard opens)
- **Eye icon** inside password field to show/hide password
- **Auto-reconnect** on WiFi drop with API refresh
- Changes the Pi system WiFi (via nmcli/wpa_cli)
- Saves WiFi config for boot persistence

### AquaGPT Chat (AI Assistant)
- Tap **water drop icon** to open fullscreen chat
- **Built-in GTK keyboard** with toggle button
- **Typing animation** for bot responses
- **Voice answers** via Google TTS (with espeak fallback)
- Built-in water Q&A (TDS, pH, water quality, saving tips)
- DuckDuckGo API for general questions
- Mic button (ready for voice input)

### Reliability
- **Deadlock prevention** — fetch lock with 20s timeout
- **Auto-announcing crash protection** — try/finally always resets flags
- **Float body handling** — prevents crash on numeric alert bodies
- **Audio cache cleanup** — old /tmp files cleaned daily
- **All timers stop on logout** — no ghost threads
- **Token cleared on logout** — prevents stale auth

## Requirements

### Hardware
- Raspberry Pi 4
- 5-inch HDMI display (800x480)
- Speaker via 3.5mm audio jack (uses PipeWire default device)
- Internet connection (WiFi)

### Software Dependencies
```bash
sudo apt-get install -y espeak ffmpeg fonts-noto-core \
    fonts-lohit-telu fonts-lohit-knda fonts-lohit-taml \
    fonts-lohit-deva fonts-lohit-mlym wvkbd
pip3 install gTTS requests --break-system-packages
```

## Setup

```bash
mkdir -p ~/Desktop/Aquabox
cp aquabox_alerts.py ~/Desktop/Aquabox/
cp *.jpg *.png ~/Desktop/Aquabox/
cp AquaBox-Alerts.desktop ~/Desktop/
chmod +x ~/Desktop/AquaBox-Alerts.desktop
```

### Autostart Service
```bash
sudo tee /etc/systemd/system/aquabox-alerts.service << 'SERVICE'
[Unit]
Description=AquaBox Alerts Display
After=graphical.target
[Service]
Type=simple
User=aquabox
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=GDK_BACKEND=wayland
ExecStartPre=/bin/bash -c "while [ ! -e /run/user/1000/wayland-0 ]; do sleep 0.5; done"
ExecStartPre=/bin/sleep 3
ExecStart=/usr/bin/python3 /home/aquabox/Desktop/Aquabox/aquabox_alerts.py
Restart=on-failure
RestartSec=5
[Install]
WantedBy=graphical.target
SERVICE
sudo systemctl daemon-reload && sudo systemctl enable aquabox-alerts.service
```

### First Time Setup
1. Tap **Admin** on login page, enter `admin` / `admin`
2. Set API credentials, **Test Connection**, then **Save**
3. Login with same credentials
4. Select TTS language from header dropdown

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| API Refresh | 120 seconds | `REFRESH_INTERVAL` |
| Token Refresh | 3hr 50min | `TOKEN_REFRESH` |
| Offline Announce | 3 hours | `OFFLINE_ANNOUNCE_INTERVAL` |
| Fetch Lock Timeout | 20 seconds | `FETCH_LOCK_TIMEOUT` |
| Audio Device | PipeWire default | `aplay -D default` |

## Files
| File | Purpose |
|------|---------|
| `aquabox_alerts.py` | Main application (GTK3 + Wayland) |
| `admin_config.json` | API credentials (auto-created) |
| `user_session.json` | Login session (auto-created) |
| `announced_alerts.json` | Tracked announced alert IDs |
| `AquaBox-Alerts.desktop` | Desktop shortcut |
| `Fluxgen-Logo.png` | Login page logo |
| `aquagpt-logo.png` | Water drop mascot |
| `fluxgen-icon.jpg` | Bot avatar in chat |
| `mic.jpg` | Mic button icon |

---

Built by **Fluxgen Sustainable Technologies** — *Build a Water-Positive Future*
