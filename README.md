# AquaBox Alerts Display System

A fullscreen alerts dashboard for Raspberry Pi with 5-inch HDMI display, built for **Fluxgen Sustainable Technologies**.

Fetches real-time water management alerts from the AquaGen API and displays them on a touchscreen with text-to-speech announcement capability.

## Features

### Login & Security
- User authentication via AquaGen API
- Session persistence (auto-login on reboot)
- Logout button with session clear
- Virtual on-screen keyboard for touchscreen input
- Animated login page with Fluxgen logo and water effects

### Alerts Dashboard
- **Read / Unread sections** — alerts separated with visual indicators
- **Color-coded cards** by importance (High=Red, Medium=Yellow, Low=Blue)
- **Auto-refresh** every 2 minutes with live countdown timer
- **Manual refresh** button
- **Mark as Read** — tap any alert to mark it read via API
- **Real-time clock** with date display

### Text-to-Speech Announcements
- **Google TTS** — natural Indian English female voice
- **Announce** individual alerts with typing animation overlay
- **Announce All Alerts** — reads every alert one by one
- **Announce Offline Units** — reads offline device alerts
- **Auto-announce offline** alerts every 2 hours
- **Cancel** button to stop announcements mid-way
- **Pre-cached audio** — instant playback, no delay
- **Synced animation** — typing text appears while voice speaks

### Display
- Optimized for **800x480** (5-inch HDMI display)
- White background with professional layout
- Scrollable alert list
- Stats bar: Unread / Read / Total / Offline counts
- Bottom status bar with API refresh timestamp

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
WorkingDirectory=/home/aquabox/Desktop/Aquabox
ExecStart=/usr/bin/python3 /home/aquabox/Desktop/Aquabox/aquabox_alerts.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable aquabox-alerts.service
sudo systemctl start aquabox-alerts.service
```

### 3. Login
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
| `OFFLINE_ANNOUNCE_INTERVAL` | 7200s | Auto-announce offline alerts interval |

## Audio Output
Default audio output is the **3.5mm headphone jack** (`plughw:2,0`).

---

Built by **Fluxgen Sustainable Technologies** — *Build a Water-Positive Future*
