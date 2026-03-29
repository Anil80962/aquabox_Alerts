# AquaBox Alerts Display System

A fullscreen alerts dashboard for Raspberry Pi with 5-inch HDMI display, built for **Fluxgen Sustainable Technologies**.

Real-time water management alerts with multi-language TTS and AI chat assistant.

## Features

### Login & Security
- **Admin settings** — fullscreen with dark blue wave animation
- **API credentials** configured via admin page (`admin` / `admin`)
- User login validates against admin-configured credentials
- Session persistence (auto-login on reboot)
- Logout waits for announce completion
- Animated login page with Fluxgen logo and water effects
- Virtual keyboard + password eye toggle

### Alerts Dashboard
- **Read / Unread sections** with clickable stat boxes
- **Color-coded cards** by importance
- **Auto-refresh** every 2 minutes with live countdown
- **Mark as Read** via API
- **Instant counter updates**

### Multi-Language TTS (6 Languages)
| Language | Code | Translations |
|----------|------|-------------|
| English | ENG | Default |
| Telugu | TEL | నిండింది, నీటి మట్టం పై పరిమితి... |
| Kannada | KAN | ತುಂಬಿದೆ, ನೀರಿನ ಮಟ್ಟ ಮೇಲಿನ ಮಿತಿ... |
| Tamil | TAM | நிரம்பியது, நீர் மட்டம் மேல் வரம்பை... |
| Hindi | HIN | भरा हुआ, जल स्तर ऊपरी सीमा... |
| Malayalam | MAL | നിറഞ്ഞു, ജല നിരപ്പ് ഉയർന്ന പരിധി... |

### Announcements
- **Smart auto-announce** — only NEW unread alerts (tracks IDs)
- **Announce All** — pre-generates audio, plays sequentially
- **Announce Offline** — with typing animation
- **Queue-based refresh** — refresh waits during announce
- **No double voices** — single announce lock
- **Dynamic typing speed** synced with audio
- **Cancel** stops instantly

### AquaBox Chat (AI Assistant)
- Tap **water drop icon** to open fullscreen chat
- **Fluxgen icon** as bot avatar
- **Typing animation** for bot responses
- **Voice answers** — spoken through speaker via Google TTS
- **Pre-generated audio** — no delay between text and voice
- Built-in water Q&A (TDS, pH, water quality, saving tips)
- DuckDuckGo API for general questions
- Mic button (ready for voice input)

### Mascot
- **Water drop + AquaBox** always visible bottom-right
- Rotating messages every 10 seconds
- Non-intrusive overlay

### Desktop App
- `AquaBox-Alerts.desktop` shortcut
- Auto-starts on boot via systemd

## Requirements

### Hardware
- Raspberry Pi 4
- 5-inch HDMI display (800x480)
- Speaker via 3.5mm audio jack
- Internet connection

### Install
```bash
sudo apt-get install -y espeak-ng ffmpeg wvkbd fonts-noto-core \
    fonts-lohit-telu fonts-lohit-knda fonts-lohit-taml \
    fonts-lohit-deva fonts-lohit-mlym
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

### Systemd Service
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
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
ExecStartPre=/bin/bash -c "while [ ! -e /run/user/1000/wayland-0 ]; do sleep 0.5; done"
ExecStartPre=/bin/sleep 1
ExecStart=/usr/bin/python3 /home/aquabox/Desktop/Aquabox/aquabox_alerts.py
Restart=on-failure
RestartSec=3
[Install]
WantedBy=graphical.target
SERVICE
sudo systemctl daemon-reload && sudo systemctl enable aquabox-alerts.service
```

### First Time
1. Tap **⚙ Admin** → `admin` / `admin`
2. Set API credentials → **Test Connection** → **Save**
3. Login with same credentials
4. Select language from header dropdown

## Assets
| File | Purpose |
|------|---------|
| `aquabox_alerts.py` | Main application |
| `AquaBox-Alerts.desktop` | Desktop shortcut |
| `fluxgen-icon.jpg` | Bot avatar in chat |
| `aquagpt-logo.png` | Water drop mascot |
| `mic.jpg` | Mic button icon |

---

Built by **Fluxgen Sustainable Technologies** — *Build a Water-Positive Future*
