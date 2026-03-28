# AquaBox Alerts Display System

A fullscreen alerts dashboard for Raspberry Pi with 5-inch HDMI display, built for **Fluxgen Sustainable Technologies**.

Fetches real-time water management alerts from the AquaGen API and displays them on a touchscreen with text-to-speech announcement capability.

## Features

### Login & Security
- **Admin settings** page to configure API credentials (`admin` / `admin`)
- User login validates against admin-configured credentials
- Session persistence (auto-login on reboot until logout)
- Logout waits for announce to complete before logging out
- Animated login page with Fluxgen logo and water effects
- Virtual on-screen keyboard (wvkbd) for touchscreen input
- Password visibility toggle (eye icon)

### Alerts Dashboard
- **Read / Unread sections** — alerts separated with visual indicators
- **Clickable stat boxes** — tap UNREAD/READ/TOTAL/OFFLINE to scroll to section
- **Color-coded cards** by importance (High=Red, Medium=Yellow, Low=Blue)
- **Auto-refresh** every 2 minutes with live countdown timer
- **Manual refresh** button
- **Mark as Read** — tap alert → "Mark Read" button → calls API
- **Real-time clock** with date display
- Instant counter updates on read/announce

### Text-to-Speech Announcements
- **Google TTS** — natural Indian English female voice (`co.in`)
- **Smart auto-announce** — only NEW unread alerts announced (tracks IDs)
- **Announce All Alerts** — pre-generates all audio, plays sequentially
- **Announce Offline Units** — reads offline device alerts with animation
- **Single announce** — tap ♪ on any alert card
- **Cancel** button (✕) stops instantly
- **Queue-based refresh** — if announce running, refresh waits in queue
- **No double voices** — `_auto_announcing` flag prevents overlap
- **Dynamic typing speed** — auto-calculated to match audio duration
- **Synced animation** — typing text and voice play simultaneously
- **Typing completion wait** — next alert starts only after current finishes
- **Batch mode** — no overlay flicker between alerts
- **Audio filters** — volume boost, highpass/lowpass for clear voice

### Display
- Optimized for **800x480** (5-inch HDMI display)
- White background with 20px uniform font size
- Scrollable alert list
- Stats bar: Unread / Read / Total / Offline counts (clickable)
- Bottom status bar with API refresh timestamp and countdown

### Boot Experience
- Auto-login (no greeter)
- Black desktop background (no desktop flash)
- Clean transition to alerts app
- Hidden console output

## Requirements

### Hardware
- Raspberry Pi 4
- 5-inch HDMI display (800x480)
- Speaker via 3.5mm audio jack
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

### 3. Auto-login
```bash
sudo tee /etc/lightdm/lightdm.conf.d/50-autologin.conf << 'CONF'
[Seat:*]
autologin-user=aquabox
autologin-session=rpd-labwc
CONF
```

### 4. First Time Setup
1. Tap **⚙ Admin** on login page
2. Enter admin credentials: `admin` / `admin`
3. Set API username and password
4. Tap **Test Connection** to verify
5. Tap **Save**
6. Login with the same credentials

## Architecture

### Queue-Based Processing
```
Announce running → API refresh triggers → QUEUED
                                           ↓
Announce finishes → Queue detected → Refresh runs → New unread? → Auto-announce
```

### Smart Auto-Announce
```
Refresh 1: 5 unread → auto-reads all 5 → tracks IDs
Refresh 2: same 5 (read) + 1 new → only reads the 1 new one
Refresh 3: no new unread → nothing announced
```

### Logout Queue
```
Announce running → tap logout → waits for completion → then logs out
No announce → tap logout → immediate logout
```

## API Endpoints

| API | Method | Purpose |
|-----|--------|---------|
| `/api/user/user/login` | GET | Authentication & token |
| `/api/user/alerts` | GET | Fetch daily alerts |
| `/api/user/notification/updateRead` | PATCH | Mark alerts as read |

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `REFRESH_INTERVAL` | 120s | Alert refresh interval |
| `TOKEN_REFRESH` | 13800s | Token refresh (10 min before 4hr expiry) |
| Audio device | `plughw:0,0` | 3.5mm headphone jack |
| Typing speed | Dynamic (0.85x audio) | Synced with voice |
| TTS voice | Google `en` `co.in` | Indian English female |
| Admin credentials | `admin` / `admin` | For API settings page |

---

Built by **Fluxgen Sustainable Technologies** — *Build a Water-Positive Future*
