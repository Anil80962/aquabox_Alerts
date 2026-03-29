# AquaBox Alerts Display System

A fullscreen alerts dashboard for Raspberry Pi with 5-inch HDMI display, built for **Fluxgen Sustainable Technologies**.

Fetches real-time water management alerts from the AquaGen API and displays them on a touchscreen with multi-language text-to-speech announcement.

## Features

### Login & Security
- **Admin settings** page to configure API credentials (`admin` / `admin`)
- User login validates against admin-configured credentials
- Session persistence (auto-login on reboot until logout)
- Logout waits for announce to complete before logging out
- Animated login page with Fluxgen logo and water effects
- Virtual on-screen keyboard (wvkbd)
- Password visibility toggle

### Multi-Language TTS
- **6 Languages**: English, Telugu, Kannada, Tamil, Hindi, Malayalam
- **Header dropdown** to switch language instantly
- Location names stay in English, everything else in local language
- Translated phrases: filled, stock upper/lower limit, daily limit, offline, etc.
- Google TTS with proper Indic fonts (Noto Sans, Lohit)

### Alerts Dashboard
- **Read / Unread sections** with visual indicators
- **Clickable stat boxes** — tap to scroll to section
- **Smart auto-announce** — only NEW unread alerts announced (tracks IDs)
- **Announce All Alerts** — pre-generates audio, plays sequentially
- **Announce Offline Units** — with typing animation
- **Cancel** button (✕) stops instantly
- **Queue-based refresh** — refresh waits if announce is running
- **No double voices** — single announce lock
- **Dynamic typing speed** synced with audio duration
- Instant counter updates on read/announce

### Desktop App
- **AquaBox-Alerts.desktop** shortcut on desktop
- Click to reopen alerts if window closes
- Auto-starts on boot via systemd

### Boot Experience
- Auto-login (no greeter)
- Black desktop background
- Clean transition to alerts app

## Requirements

### Hardware
- Raspberry Pi 4
- 5-inch HDMI display (800x480)
- Speaker via 3.5mm audio jack
- Internet connection

### Software & Fonts
```bash
# Dependencies
sudo apt-get install -y espeak-ng ffmpeg wvkbd
pip3 install gTTS requests --break-system-packages

# Indic language fonts
sudo apt-get install -y fonts-noto-core fonts-noto-extra \
    fonts-lohit-telu fonts-lohit-knda fonts-lohit-taml \
    fonts-lohit-deva fonts-lohit-mlym
```

## Setup

### 1. Copy files
```bash
mkdir -p ~/Desktop/Aquabox
cp aquabox_alerts.py ~/Desktop/Aquabox/
cp Fluxgen-Logo.png ~/Desktop/Aquabox/
cp AquaBox-Alerts.desktop ~/Desktop/
chmod +x ~/Desktop/AquaBox-Alerts.desktop
```

### 2. Create systemd service
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

sudo systemctl daemon-reload
sudo systemctl enable aquabox-alerts.service
sudo systemctl start aquabox-alerts.service
```

### 3. First Time Setup
1. Tap **⚙ Admin** → `admin` / `admin`
2. Set API username and password
3. **Test Connection** → Save
4. Login with same credentials
5. Select language from header dropdown

## Supported Languages

| Language | Code | Dropdown | Translations |
|----------|------|----------|-------------|
| English | en | ENG | Default |
| Telugu | te | TEL | నిండింది, నీటి మట్టం పై పరిమితి... |
| Kannada | kn | KAN | ತುಂಬಿದೆ, ನೀರಿನ ಮಟ್ಟ ಮೇಲಿನ ಮಿತಿ... |
| Tamil | ta | TAM | நிரம்பியது, நீர் மட்டம் மேல் வரம்பை... |
| Hindi | hi | HIN | भरा हुआ, जल स्तर ऊपरी सीमा... |
| Malayalam | ml | MAL | നിറഞ്ഞു, ജല നിരപ്പ് ഉയർന്ന പരിധി... |

## Architecture

### Queue-Based Processing
```
Announce running → Refresh triggers → QUEUED → Announce done → Refresh runs
```

### Smart Auto-Announce
```
Boot → marks all existing alerts as known → only NEW alerts get announced
```

## API Endpoints

| API | Method | Purpose |
|-----|--------|---------|
| `/api/user/user/login` | GET | Authentication |
| `/api/user/alerts` | GET | Fetch daily alerts |
| `/api/user/notification/updateRead` | PATCH | Mark as read |

## Configuration

| Setting | Value |
|---------|-------|
| Refresh interval | 120s |
| Token refresh | 13800s (10 min before 4hr expiry) |
| Audio device | plughw:0,0 |
| Admin credentials | admin / admin |

---

Built by **Fluxgen Sustainable Technologies** — *Build a Water-Positive Future*
