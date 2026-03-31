# AquaBox Alerts - ZEST MEATER CODE

A GTK-based alert display system for Raspberry Pi 4, built for **Fluxgen Sustainable Technologies**. Monitors water infrastructure via the AquaGen API and displays real-time alerts on a 5-inch HDMI touchscreen.

## Features

### Alert Display
- Fetches alerts from AquaGen production API
- Color-coded alert cards (High/Medium/Low/Info)
- Unread/Read/Offline alert sections with counters
- Auto-refreshes every 120 seconds
- Scrollable alert list optimized for 800x480 display

### Text-to-Speech (TTS) Announcements
- Auto-announces unread alerts with typing animation
- Multi-language support: English, Telugu, Hindi, Kannada, Tamil
- Individual and batch alert announcements
- Offline unit announcements (hourly)
- Typing animation synced with TTS audio in selected language
- Cancel announcements mid-way with immediate button reset

### WiFi Manager (Bottom Bar)
- WiFi icon in bottom-left corner with live status
- **White icon** = connected, **Red icon with X** = disconnected
- Checks WiFi status every 5 seconds
- Auto-reconnects on WiFi drop using `wpa_cli`
- Auto-refreshes API alerts on reconnect
- **Tap WiFi icon** to open WiFi Settings panel:
  - Page 1: Shows current connection, scan for available networks
  - Page 2: Select network, enter password with on-screen keyboard, Save & Connect
  - Uses `nmcli` (NetworkManager) for reliable connections
  - Saves credentials for boot persistence

### Volume Control (Bottom Bar)
- Speaker icon next to WiFi icon
- Tap to show volume slider (0-100%)
- Adjusts system volume via `amixer` in real-time

### AquaGPT Chat
- AI-powered water assistant chatbot
- Voice input support
- Context-aware answers about water management

### Other Features
- Login screen with admin settings
- Language selection dropdown in header
- Live clock and date display
- AquaGPT mascot with animated messages
- Bluetooth audio support
- WiFi hotspot setup mode (AP mode)

## Hardware

- Raspberry Pi 4 (4GB RAM)
- 5-inch HDMI touchscreen (800x480)
- WiFi (wlan0)
- Optional: Bluetooth speaker

## Deployment

The main application runs as a systemd service on the Pi:

```bash
# Service file: /etc/systemd/system/aquabox-alerts.service
sudo systemctl enable aquabox-alerts
sudo systemctl start aquabox-alerts
```

### SSH Access (via Tailscale)
```bash
ssh aquabox@100.78.44.6
```

## Project Structure

| File | Description |
|------|-------------|
| `aquabox_alerts.py` | Main GTK application (alerts, TTS, WiFi, volume, chat) |
| `wifi_manager.py` | Standalone WiFi manager with AP hotspot mode |
| `tts_service.py` | TTS Flask service |
| `calibration_system.py` | Sensor calibration system |
| `connect_bt.py` | Bluetooth speaker connection |
| `bt_scan.py` / `bt_setup.py` | Bluetooth scanning and setup |
| `ZEST_MEATER_CODE.ino` | Arduino/ESP32 IoT firmware |
| `google_apps_script.js` | Google Apps Script integration |
| `AquaBox-Alerts.desktop` | Desktop autostart entry |

## Dependencies

- Python 3 with GTK 3 (`gi`, `Gtk`, `Gdk`, `cairo`)
- `requests`, `flask`, `paramiko`
- `gTTS` (Google Text-to-Speech)
- `ffmpeg`, `aplay` (audio processing/playback)
- `nmcli` (NetworkManager), `wvkbd-mobintl` (on-screen keyboard)
- Tailscale (remote access)
