# AquaBox Alerts Display System

A fullscreen alerts dashboard for Raspberry Pi with 5-inch HDMI display, built for **Fluxgen Sustainable Technologies**.

Fetches real-time water management alerts from the AquaGen API and displays them on a touchscreen with text-to-speech announcement capability.

## Features

### Login & Security
- User authentication via AquaGen API
- Animated login page with Fluxgen logo and water effects (drops, waves, ripples)
- Session persistence (auto-login on reboot until logout)
- Logout button clears session and returns to login
- Virtual on-screen keyboard (wvkbd) for touchscreen input
- Password visibility toggle (eye icon)

### Alerts Dashboard
- **Read / Unread sections** — alerts separated with visual indicators (red dot = unread, green dot = read)
- **Color-coded cards** by importance (High=Red, Medium=Yellow, Low=Blue)
- **Clickable stat boxes** — tap UNREAD/READ/TOTAL/OFFLINE to scroll to that section
- **Auto-refresh** every 2 minutes with live countdown timer
- **Manual refresh** button
- **Mark as Read** — tap alert → "Mark Read" button → calls API
- **Real-time clock** with date display

### Text-to-Speech Announcements
- **Google TTS** — natural Indian English female voice (`co.in`)
- **Announce** individual alerts with typing animation overlay
- **Announce All Alerts** — pre-generates all audio, then plays one by one sequentially
- **Announce Offline Units** — reads offline device alerts
- **Auto-announce unread** alerts when they first appear
- **Auto-announce offline** alerts every 1 hour
- **Cancel** button (✕) to stop announcements mid-way
- **Dynamic typing speed** — auto-calculated to match audio duration (30% faster)
- **Synced animation** — typing text and voice play simultaneously
- **Typing waits for completion** — next alert only starts after current one fully finishes
- **Batch mode** — no overlay flicker between alerts during "Announce All"
- **Pre-cached audio** for faster playback
- **Audio filters** — volume boost, highpass/lowpass for clear voice

### Display
- Optimized for **800x480** (5-inch HDMI display)
- White background with professional layout
- All text **20px** uniform font size
- Scrollable alert list
- Stats bar: Unread / Read / Total / Offline counts (clickable)
- Bottom status bar with API refresh timestamp and countdown
- Instant counter updates when alerts are read/announced

### Boot Experience
- Auto-login (no greeter)
- Black desktop background (no desktop flash)
- Boot splash with Fluxgen water animation
- Clean transition to alerts app
- Hidden console output (no blue lines)

## Requirements

### Hardware
- Raspberry Pi 4
- 5-inch HDMI display (800x480)
- Speaker via 3.5mm audio jack (for TTS)
- Internet connection

### Software
```
Python 3.x
GTK 3.0 (gi)
gTTS (Google Text-to-Speech)
requests
espeak-ng (fallback TTS)
ffmpeg (audio conversion)
wvkbd (virtual keyboard)
cairo (graphics)
```

### Install Dependencies
```bash
sudo apt-get install -y espeak-ng ffmpeg wvkbd
pip3 install gTTS requests --break-system-packages
```

## Setup

### 1. Copy to Raspberry Pi
```bash
mkdir -p ~/Desktop/Aquabox
cp aquabox_alerts.py ~/Desktop/Aquabox/
cp Fluxgen-Logo.png ~/Desktop/Aquabox/
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

### 3. Auto-login (skip greeter)
```bash
sudo tee /etc/lightdm/lightdm.conf.d/50-autologin.conf << 'CONF'
[Seat:*]
autologin-user=aquabox
autologin-session=rpd-labwc
CONF
```

### 4. Login
Enter your AquaGen username and password on the touchscreen login page.

## API Endpoints Used

| API | Method | Purpose |
|-----|--------|---------|
| `/api/user/user/login` | GET | Authentication & token generation |
| `/api/user/alerts` | GET | Fetch daily alerts |
| `/api/user/notification/updateRead` | PATCH | Mark alerts as read |

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `REFRESH_INTERVAL` | 120s | Alert refresh interval |
| `TOKEN_REFRESH` | 13800s | Token refresh (10 min before 4hr expiry) |
| `OFFLINE_ANNOUNCE_INTERVAL` | 3600s | Auto-announce offline alerts interval |
| Audio device | `plughw:0,0` | 3.5mm headphone jack |
| Typing speed | Dynamic (0.7x audio) | 30% faster than voice |
| TTS voice | Google `en` `co.in` | Indian English female |

## Audio Output
Default audio output is the **3.5mm headphone jack** (`plughw:0,0`). Volume boost and audio filters applied for clarity.

---

Built by **Fluxgen Sustainable Technologies** — *Build a Water-Positive Future*
