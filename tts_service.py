#!/usr/bin/env python3
"""
AquaBox Text-to-Speech Service
Fetches unit data from API and announces via speaker.
Supports Bluetooth audio devices + AUX 3.5mm jack.
Web interface at http://<pi-ip>:8080
"""

import os
import sys
import json
import time
import re
import threading
import subprocess
import socket
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from gtts import gTTS

# ==================== CONFIGURATION ====================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_config.json")

DEFAULT_CONFIG = {
    "auth_url": "https://dev2-aquagenapi.azurewebsites.net/api/user/user/login",
    "unit_url": "https://dev2-aquagenapi.azurewebsites.net/api/user/external/latest/unit",
    "username": "elcitauser",
    "password_auth": "Elcita@2222!",
    "unit_id": "FG24869L",
    "speak_interval": 60,
    "volume": 90,
    "speed": 150,
    "language": "en",
    "voice": "en+f3",
    "tts_engine": "google",
    "google_lang": "en",
    "google_tld": "co.in",
    "enabled": True,
    "audio_output": "auto",
    "audio_device": "plughw:2,0",
    "bt_device_mac": "",
    "bt_device_name": "",
    "announce_location": True,
    "announce_value": True,
    "announce_time": True,
}

# ==================== GLOBALS ====================

app = Flask(__name__)
config = {}
token = ""
token_expiry = 0
last_data = {
    "value": 0.0,
    "unit": "%",
    "location": "N/A",
    "last_update": "N/A",
    "fetched_at": "Never"
}
tts_thread = None
tts_running = False
speak_lock = threading.Lock()

# Pre-cached audio files for instant playback
CACHE_DIR = "/tmp/aquabox_audio_cache"
cached_speak_mp3 = ""
cached_speak_text = ""
cache_lock = threading.Lock()
bt_scan_lock = threading.Lock()
bt_scanning = False
bt_scan_results = []

# ==================== CONFIG MANAGEMENT ====================

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            config = {**DEFAULT_CONFIG, **saved}
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            config = DEFAULT_CONFIG.copy()
    else:
        config = DEFAULT_CONFIG.copy()
        save_config()
    return config


def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# ==================== BLUETOOTH FUNCTIONS ====================

def bt_run(cmd, timeout=10):
    """Run a bluetoothctl command and return output."""
    try:
        result = subprocess.run(
            ["bluetoothctl"] + cmd.split(),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() + "\n" + result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return f"error: {e}"


def bt_power_on():
    """Ensure Bluetooth is powered on and unblocked."""
    subprocess.run(["sudo", "rfkill", "unblock", "bluetooth"],
                   capture_output=True, timeout=5)
    time.sleep(1)
    bt_run("power on")
    time.sleep(1)


def bt_get_status():
    """Get Bluetooth controller status."""
    output = bt_run("show")
    powered = "Powered: yes" in output
    return {"powered": powered, "raw": output}


def bt_scan_devices():
    """Scan for nearby Bluetooth devices."""
    global bt_scanning, bt_scan_results
    with bt_scan_lock:
        if bt_scanning:
            return bt_scan_results
        bt_scanning = True

    try:
        bt_power_on()

        # Clear old devices
        bt_run("scan off", timeout=3)
        time.sleep(0.5)

        # Start scan
        proc = subprocess.Popen(
            ["bluetoothctl", "--timeout", "12", "scan", "on"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

        time.sleep(1)

        # Get all devices
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True, text=True, timeout=5
        )
        devices = []
        for line in result.stdout.strip().split("\n"):
            match = re.match(r"Device\s+([0-9A-F:]{17})\s+(.+)", line)
            if match:
                mac = match.group(1)
                name = match.group(2)
                # Get device info
                info = bt_get_device_info(mac)
                devices.append({
                    "mac": mac,
                    "name": name,
                    "paired": info.get("paired", False),
                    "connected": info.get("connected", False),
                    "trusted": info.get("trusted", False),
                    "icon": info.get("icon", "unknown"),
                })

        bt_scan_results = devices
        return devices
    finally:
        with bt_scan_lock:
            bt_scanning = False


def bt_get_device_info(mac):
    """Get detailed info about a specific device."""
    output = bt_run(f"info {mac}")
    return {
        "paired": "Paired: yes" in output,
        "connected": "Connected: yes" in output,
        "trusted": "Trusted: yes" in output,
        "icon": _extract_field(output, "Icon"),
    }


def _extract_field(text, field):
    """Extract a field value from bluetoothctl output."""
    for line in text.split("\n"):
        if f"{field}:" in line:
            return line.split(":", 1)[1].strip()
    return ""


def bt_pair_and_connect(mac):
    """Pair, trust, and connect to a Bluetooth device."""
    bt_power_on()

    # Trust first
    print(f"[{now()}] Trusting {mac}...")
    bt_run(f"trust {mac}", timeout=5)
    time.sleep(1)

    # Pair
    info = bt_get_device_info(mac)
    if not info["paired"]:
        print(f"[{now()}] Pairing with {mac}...")
        output = bt_run(f"pair {mac}", timeout=15)
        print(f"[{now()}] Pair result: {output}")
        time.sleep(2)

    # Connect
    print(f"[{now()}] Connecting to {mac}...")
    output = bt_run(f"connect {mac}", timeout=15)
    print(f"[{now()}] Connect result: {output}")
    time.sleep(3)

    # Verify
    info = bt_get_device_info(mac)
    if info["connected"]:
        # Update config with connected BT device
        config["bt_device_mac"] = mac
        # Find name from scan results
        for dev in bt_scan_results:
            if dev["mac"] == mac:
                config["bt_device_name"] = dev["name"]
                break
        config["audio_output"] = "bluetooth"
        save_config()
        return True, "Connected successfully"
    else:
        return False, "Connection failed. Make sure the device is in pairing mode."


def bt_disconnect(mac):
    """Disconnect a Bluetooth device."""
    output = bt_run(f"disconnect {mac}", timeout=10)
    time.sleep(1)
    info = bt_get_device_info(mac)
    if not info["connected"]:
        if config.get("bt_device_mac") == mac:
            config["audio_output"] = "aux"
            save_config()
        return True, "Disconnected"
    return False, "Disconnect failed"


def bt_remove(mac):
    """Remove/unpair a Bluetooth device."""
    bt_run(f"disconnect {mac}", timeout=5)
    time.sleep(0.5)
    output = bt_run(f"remove {mac}", timeout=10)
    if config.get("bt_device_mac") == mac:
        config["bt_device_mac"] = ""
        config["bt_device_name"] = ""
        config["audio_output"] = "aux"
        save_config()
    return True, "Device removed"


def bt_get_connected_audio():
    """Get list of connected Bluetooth audio devices and their ALSA/PipeWire sink."""
    connected = []
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices", "Connected"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            match = re.match(r"Device\s+([0-9A-F:]{17})\s+(.+)", line)
            if match:
                connected.append({"mac": match.group(1), "name": match.group(2)})
    except Exception:
        pass
    return connected


def get_audio_device_for_playback():
    """Determine the best audio device for playback."""
    output_mode = config.get("audio_output", "auto")

    if output_mode == "bluetooth" and config.get("bt_device_mac"):
        # Check if BT device is still connected
        info = bt_get_device_info(config["bt_device_mac"])
        if info["connected"]:
            return "bluetooth"

    if output_mode == "aux" or output_mode == "auto":
        return "aux"

    return "aux"

# ==================== API FUNCTIONS ====================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_token():
    global token, token_expiry
    try:
        headers = {
            "accept": "application/json",
            "username": config["username"],
            "password": config["password_auth"],
            "LoginType": "EXTERNAL"
        }
        resp = requests.get(config["auth_url"], headers=headers, timeout=15, verify=False)
        if resp.status_code in (200, 201):
            data = resp.json()
            t = data.get("token") or data.get("data", {}).get("token", "")
            if t:
                token = t.replace("Bearer ", "")
                token_expiry = time.time() + 3600
                print(f"[{now()}] Token fetched successfully")
                return True
        print(f"[{now()}] Token fetch failed: HTTP {resp.status_code}")
        return False
    except Exception as e:
        print(f"[{now()}] Token fetch error: {e}")
        return False


def fetch_unit_data():
    global last_data, token, token_expiry
    if time.time() > token_expiry:
        if not fetch_token():
            return None
    try:
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        url = f"{config['unit_url']}?unitId={config['unit_id']}"
        resp = requests.get(url, headers=headers, timeout=10, verify=False)

        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                unit = data["data"][0]
                value = unit.get("value", 0.0)
                display_unit = unit.get("displayUnit", "%")
                if display_unit == "L":
                    display_unit = "%"
                location = unit.get("locationName", "Unknown")
                updated = unit.get("createdOn", "N/A")

                last_data = {
                    "value": value,
                    "unit": display_unit,
                    "location": location,
                    "last_update": updated,
                    "fetched_at": now()
                }
                print(f"[{now()}] Data: {value}{display_unit} at {location}")
                return last_data
        elif resp.status_code in (401, 440):
            print(f"[{now()}] Token expired, refreshing...")
            token = ""
            token_expiry = 0
        else:
            print(f"[{now()}] Unit fetch failed: HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"[{now()}] Unit fetch error: {e}")
        return None

# ==================== TTS FUNCTIONS ====================

def generate_audio(text, out_path, use_google=None):
    """Generate audio file from text. Returns True on success."""
    engine = use_google if use_google is not None else (config.get("tts_engine", "google") == "google")

    if engine:
        try:
            lang = config.get("google_lang", "en")
            tld = config.get("google_tld", "co.in")
            tts = gTTS(text=text, lang=lang, tld=tld)
            mp3_path = out_path + ".mp3"
            tts.save(mp3_path)
            # Convert MP3 to WAV for device playback
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", out_path],
                capture_output=True, timeout=30
            )
            os.remove(mp3_path)
            print(f"[{now()}] Generated audio (google): {text[:50]}")
            return True
        except Exception as e:
            print(f"[{now()}] gTTS error: {e}, falling back to espeak-ng")

    # Fallback: espeak-ng
    result = subprocess.run([
        "espeak-ng",
        "-v", config.get("voice", "en+f3"),
        "-s", str(config.get("speed", 150)),
        "-a", str(config.get("volume", 90)),
        "-w", out_path,
        text
    ], capture_output=True, timeout=15)
    if result.returncode != 0:
        print(f"[{now()}] espeak-ng error: {result.stderr.decode('utf-8', errors='replace')}")
        return False
    return True


def generate_audio_mp3(text, out_path):
    """Generate MP3 audio for browser streaming (smaller file, faster load)."""
    try:
        lang = config.get("google_lang", "en")
        tld = config.get("google_tld", "co.in")
        tts = gTTS(text=text, lang=lang, tld=tld)
        tts.save(out_path)
        return True
    except Exception as e:
        print(f"[{now()}] gTTS MP3 error: {e}, using espeak-ng + ffmpeg")
        wav_path = out_path + ".wav"
        subprocess.run([
            "espeak-ng",
            "-v", config.get("voice", "en+f3"),
            "-s", str(config.get("speed", 150)),
            "-a", str(config.get("volume", 90)),
            "-w", wav_path,
            text
        ], capture_output=True, timeout=15)
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "128k", out_path],
            capture_output=True, timeout=15
        )
        try:
            os.remove(wav_path)
        except Exception:
            pass
        return os.path.exists(out_path)


def speak(text):
    """Speak text through Bluetooth (pw-play) or AUX (aplay)."""
    acquired = speak_lock.acquire(timeout=35)
    if not acquired:
        print(f"[{now()}] Speak lock busy, skipping: {text[:50]}")
        return False
    tmp_wav = "/tmp/aquabox_tts.wav"
    try:
        audio_mode = get_audio_device_for_playback()

        if not generate_audio(text, tmp_wav):
            return False

        if audio_mode == "bluetooth":
            env = os.environ.copy()
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"
            play_result = subprocess.run(
                ["pw-play", tmp_wav],
                capture_output=True, timeout=30, env=env
            )
            if play_result.returncode != 0:
                err_msg = play_result.stderr.decode("utf-8", errors="replace")
                print(f"[{now()}] pw-play error: {err_msg}")
                return False
        else:
            play_result = subprocess.run(
                ["aplay", "-D", config.get("audio_device", "plughw:2,0"), "-q", tmp_wav],
                capture_output=True, timeout=30
            )
            if play_result.returncode != 0:
                err_msg = play_result.stderr.decode("utf-8", errors="replace")
                print(f"[{now()}] aplay error: {err_msg}")
                return False

        print(f"[{now()}] Spoke ({audio_mode}): {text}")
        return True
    except Exception as e:
        print(f"[{now()}] TTS error: {e}")
        return False
    finally:
        speak_lock.release()
        try:
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)
        except Exception:
            pass


def build_announcement(data):
    """Build the announcement text from unit data."""
    parts = []

    if config.get("announce_location", True) and data["location"] != "N/A":
        parts.append(f"Location: {data['location']}.")

    if config.get("announce_value", True):
        value = data["value"]
        unit = data["unit"]
        unit_name = "percent" if unit == "%" else unit
        parts.append(f"Current reading is {value:.1f} {unit_name}.")

    if config.get("announce_time", True) and data["last_update"] != "N/A":
        parts.append(f"Last updated at {data['last_update']}.")

    if not parts:
        parts.append(f"Reading is {data['value']:.1f}")

    return " ".join(parts)


def update_audio_cache(text=None):
    """Pre-generate MP3 for instant phone playback."""
    global cached_speak_mp3, cached_speak_text
    if text is None:
        data = last_data
        text = build_announcement(data)
    if text == cached_speak_text and cached_speak_mp3 and os.path.exists(cached_speak_mp3):
        return  # Already cached
    with cache_lock:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            out_path = os.path.join(CACHE_DIR, "speak.mp3")
            if generate_audio_mp3(text, out_path):
                cached_speak_mp3 = out_path
                cached_speak_text = text
                print(f"[{now()}] Audio cache updated: {text[:50]}")
        except Exception as e:
            print(f"[{now()}] Cache update error: {e}")


def tts_loop():
    """Main TTS loop - fetches data and speaks it periodically."""
    global tts_running
    print(f"[{now()}] TTS service started (interval: {config['speak_interval']}s)")

    while tts_running:
        try:
            if config.get("enabled", True):
                data = fetch_unit_data()
                if data:
                    announcement = build_announcement(data)
                    # Pre-cache audio for phone playback (runs in background)
                    threading.Thread(target=update_audio_cache, args=(announcement,), daemon=True).start()
                    speak(announcement)
                else:
                    print(f"[{now()}] No data to announce")

            for _ in range(config.get("speak_interval", 60)):
                if not tts_running:
                    break
                time.sleep(1)

        except Exception as e:
            print(f"[{now()}] TTS loop error: {e}")
            time.sleep(5)

    print(f"[{now()}] TTS service stopped")


def start_tts():
    global tts_thread, tts_running
    if tts_running:
        return False
    tts_running = True
    tts_thread = threading.Thread(target=tts_loop, daemon=True)
    tts_thread.start()
    return True


def stop_tts():
    global tts_running
    tts_running = False
    return True

# ==================== WEB UI ====================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AquaBox TTS Control</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
    min-height: 100vh; padding: 15px; color: #fff;
  }
  .container { max-width: 460px; margin: 0 auto; }
  .card {
    background: rgba(255,255,255,0.08); backdrop-filter: blur(10px);
    border-radius: 16px; padding: 20px; margin-bottom: 15px;
    border: 1px solid rgba(255,255,255,0.12);
  }
  h1 { text-align: center; font-size: 22px; margin-bottom: 4px; }
  .subtitle { text-align: center; font-size: 12px; color: #888; margin-bottom: 15px; }
  h2 { font-size: 16px; color: #4fc3f7; margin-bottom: 12px; }
  .data-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .data-item { text-align: center; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 10px; }
  .data-item .label { font-size: 11px; color: #888; text-transform: uppercase; }
  .data-item .value { font-size: 22px; font-weight: 700; color: #4fc3f7; margin-top: 4px; }
  .data-item.full { grid-column: 1 / -1; }
  .data-item .value.small { font-size: 14px; }

  .status-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 600;
  }
  .status-on { background: rgba(0,200,100,0.2); color: #00c864; }
  .status-off { background: rgba(255,60,60,0.2); color: #ff3c3c; }
  .status-bt { background: rgba(50,100,255,0.2); color: #4488ff; }

  label { display: block; font-size: 13px; color: #aaa; margin-bottom: 4px; margin-top: 12px; }
  input[type=number], input[type=text], select {
    width: 100%; padding: 10px; border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.15);
    background: rgba(255,255,255,0.06); color: #fff; font-size: 15px;
  }
  input:focus, select:focus { outline: none; border-color: #4fc3f7; }

  .slider-wrap { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
  .slider-wrap input[type=range] { flex: 1; accent-color: #4fc3f7; }
  .slider-wrap .val { min-width: 35px; text-align: center; font-size: 14px; }

  .btn-row { display: flex; gap: 10px; margin-top: 15px; }
  .btn {
    flex: 1; padding: 12px; border: none; border-radius: 10px;
    font-size: 15px; font-weight: 600; cursor: pointer; text-align: center;
  }
  .btn-sm { padding: 8px 14px; font-size: 12px; flex: none; }
  .btn-primary { background: linear-gradient(135deg, #4fc3f7, #0288d1); color: #fff; }
  .btn-success { background: linear-gradient(135deg, #66bb6a, #388e3c); color: #fff; }
  .btn-danger { background: linear-gradient(135deg, #ef5350, #c62828); color: #fff; }
  .btn-warning { background: linear-gradient(135deg, #ffa726, #e65100); color: #fff; }
  .btn-bt { background: linear-gradient(135deg, #42a5f5, #1565c0); color: #fff; }
  .btn:hover { opacity: 0.85; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .toggle-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .toggle-label { font-size: 14px; }
  .toggle { position: relative; width: 48px; height: 26px; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .toggle .slider {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(255,255,255,0.15); border-radius: 13px; cursor: pointer;
    transition: 0.3s;
  }
  .toggle .slider:before {
    content: ""; position: absolute; height: 20px; width: 20px;
    left: 3px; bottom: 3px; background: #fff; border-radius: 50%;
    transition: 0.3s;
  }
  .toggle input:checked + .slider { background: #4fc3f7; }
  .toggle input:checked + .slider:before { transform: translateX(22px); }

  .toast {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    padding: 10px 24px; border-radius: 10px; font-size: 14px;
    background: rgba(0,200,100,0.9); color: #fff; display: none; z-index: 100;
    max-width: 90%;
  }

  /* Bluetooth specific */
  .bt-device {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px; margin-bottom: 8px; border-radius: 10px;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
  }
  .bt-device.connected { border-color: rgba(0,200,100,0.4); background: rgba(0,200,100,0.08); }
  .bt-device.paired { border-color: rgba(70,130,255,0.3); }
  .bt-info { flex: 1; }
  .bt-name { font-size: 14px; font-weight: 600; }
  .bt-mac { font-size: 11px; color: #888; margin-top: 2px; }
  .bt-tags { margin-top: 4px; }
  .bt-tag {
    display: inline-block; font-size: 10px; padding: 2px 8px;
    border-radius: 8px; margin-right: 4px;
  }
  .bt-tag-connected { background: rgba(0,200,100,0.2); color: #00c864; }
  .bt-tag-paired { background: rgba(70,130,255,0.2); color: #4488ff; }
  .bt-tag-audio { background: rgba(255,165,0,0.2); color: #ffa500; }
  .bt-actions { display: flex; gap: 6px; flex-shrink: 0; }
  .bt-actions .btn-sm { min-width: 60px; }
  .bt-empty { text-align: center; padding: 20px; color: #666; font-size: 13px; }
  .bt-scanning { text-align: center; padding: 15px; color: #4fc3f7; }
  .bt-scanning .spinner {
    display: inline-block; width: 20px; height: 20px;
    border: 2px solid rgba(79,195,247,0.3); border-top-color: #4fc3f7;
    border-radius: 50%; animation: spin 1s linear infinite;
    vertical-align: middle; margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .audio-output-row {
    display: flex; gap: 8px; margin-top: 10px;
  }
  .audio-opt {
    flex: 1; padding: 10px; border-radius: 10px; text-align: center;
    cursor: pointer; font-size: 13px; font-weight: 600;
    border: 2px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03); transition: 0.3s;
  }
  .audio-opt.active { border-color: #4fc3f7; background: rgba(79,195,247,0.1); color: #4fc3f7; }
  .audio-opt:hover { border-color: rgba(255,255,255,0.3); }
  .audio-opt .icon { font-size: 22px; display: block; margin-bottom: 4px; }
</style>
</head>
<body>
<div class="container">
  <h1>AquaBox TTS</h1>
  <p class="subtitle">Text-to-Speech Control Panel</p>

  <!-- Live Data Card -->
  <div class="card">
    <h2>Live Data</h2>
    <div class="data-grid">
      <div class="data-item">
        <div class="label">Reading</div>
        <div class="value" id="val">--</div>
      </div>
      <div class="data-item">
        <div class="label">Location</div>
        <div class="value small" id="loc">--</div>
      </div>
      <div class="data-item full">
        <div class="label">Last Updated</div>
        <div class="value small" id="updated">--</div>
      </div>
    </div>
    <div style="text-align:center; margin-top:12px;">
      TTS: <span class="status-badge" id="ttsStatus">--</span>
      Audio: <span class="status-badge" id="audioStatus">--</span>
    </div>
  </div>

  <!-- Quick Actions -->
  <div class="card">
    <h2>Quick Actions</h2>
    <div class="btn-row">
      <button class="btn btn-success" onclick="apiCall('/api/start')">Start Server TTS</button>
      <button class="btn btn-danger" onclick="apiCall('/api/stop')">Stop Server TTS</button>
    </div>
    <div class="btn-row">
      <button class="btn btn-primary" onclick="browserSpeak()">Speak on Phone</button>
      <button class="btn btn-warning" onclick="testBrowserSpeak()">Test Phone Speaker</button>
    </div>
    <div class="btn-row">
      <button class="btn btn-success" id="autoSpeakBtn" onclick="toggleAutoSpeak()">Start Auto Speak</button>
    </div>
    <div id="autoSpeakStatus" style="text-align:center; margin-top:8px; font-size:12px; color:#888; display:none;">
      Auto speaking every <span id="autoSpeakInterval">60</span>s
      <span class="status-badge status-on" style="margin-left:8px;">ACTIVE</span>
    </div>
  </div>

  <!-- Bluetooth Card -->
  <div class="card">
    <h2>Bluetooth Audio</h2>

    <div style="margin-bottom: 12px;">
      <div class="toggle-row">
        <span class="toggle-label">Audio Output</span>
      </div>
      <div class="audio-output-row">
        <div class="audio-opt" id="optAux" onclick="setAudioOutput('aux')">
          <span class="icon">&#x1F50A;</span> AUX Jack
        </div>
        <div class="audio-opt" id="optBt" onclick="setAudioOutput('bluetooth')">
          <span class="icon">&#x1F399;</span> Bluetooth
        </div>
        <div class="audio-opt" id="optAuto" onclick="setAudioOutput('auto')">
          <span class="icon">&#x1F504;</span> Auto
        </div>
      </div>
    </div>

    <!-- Connected Device Display -->
    <div id="btConnected" style="display:none;">
      <div class="bt-device connected" id="btConnectedDevice">
        <div class="bt-info">
          <div class="bt-name" id="btConnName">--</div>
          <div class="bt-mac" id="btConnMac">--</div>
          <div class="bt-tags"><span class="bt-tag bt-tag-connected">Connected</span></div>
        </div>
        <div class="bt-actions">
          <button class="btn btn-sm btn-danger" onclick="btDisconnectCurrent()">Disconnect</button>
        </div>
      </div>
    </div>

    <div class="btn-row" style="margin-top: 10px; margin-bottom: 12px;">
      <button class="btn btn-bt" id="scanBtn" onclick="btScan()">Scan for Devices</button>
    </div>

    <div id="btDevices">
      <div class="bt-empty">Press "Scan for Devices" to find Bluetooth speakers</div>
    </div>
  </div>

  <!-- TTS Settings Card -->
  <div class="card">
    <h2>TTS Settings</h2>

    <label>Speak Interval (seconds)</label>
    <input type="number" id="interval" min="10" max="3600" value="60">

    <label>Volume</label>
    <div class="slider-wrap">
      <input type="range" id="volume" min="0" max="100" value="90"
             oninput="document.getElementById('volVal').textContent=this.value">
      <span class="val" id="volVal">90</span>
    </div>

    <label>Speed (words/min)</label>
    <div class="slider-wrap">
      <input type="range" id="speed" min="80" max="300" value="150"
             oninput="document.getElementById('spdVal').textContent=this.value">
      <span class="val" id="spdVal">150</span>
    </div>

    <label>Language</label>
    <select id="googleLang" onchange="updateLangPreview()">
      <option value="en|co.in">English - Indian (Natural)</option>
      <option value="en|com">English - US (Natural)</option>
      <option value="en|co.uk">English - UK (Natural)</option>
      <option value="hi|co.in">Hindi (Natural)</option>
      <option value="mr|co.in">Marathi (Natural)</option>
      <option value="ta|co.in">Tamil (Natural)</option>
      <option value="te|co.in">Telugu (Natural)</option>
      <option value="kn|co.in">Kannada (Natural)</option>
    </select>
    <div style="font-size:11px; color:#666; margin-top:4px;" id="langPreview">Powered by Google TTS - natural human voice</div>

    <div style="margin-top: 15px;">
      <div class="toggle-row">
        <span class="toggle-label">Announce Location</span>
        <label class="toggle"><input type="checkbox" id="annLoc" checked><span class="slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Announce Value</span>
        <label class="toggle"><input type="checkbox" id="annVal" checked><span class="slider"></span></label>
      </div>
      <div class="toggle-row">
        <span class="toggle-label">Announce Time</span>
        <label class="toggle"><input type="checkbox" id="annTime" checked><span class="slider"></span></label>
      </div>
    </div>

    <div class="btn-row">
      <button class="btn btn-primary" onclick="saveSettings()">Save Settings</button>
    </div>
  </div>

  <!-- API Config Card -->
  <div class="card">
    <h2>API Configuration</h2>
    <label>Unit ID</label>
    <input type="text" id="unitId" value="">
    <label>API Username</label>
    <input type="text" id="apiUser" value="">
    <label>API Password</label>
    <input type="text" id="apiPass" value="">
    <div class="btn-row">
      <button class="btn btn-primary" onclick="saveApiConfig()">Save API Config</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
function showToast(msg, color) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = color || 'rgba(0,200,100,0.9)';
  t.style.display = 'block';
  setTimeout(function() { t.style.display = 'none'; }, 3000);
}

function apiCall(url, method, body) {
  var opts = { method: method || 'POST' };
  if (body) {
    opts.headers = {'Content-Type': 'application/json'};
    opts.body = JSON.stringify(body);
  }
  return fetch(url, opts).then(function(r) { return r.json(); }).then(function(d) {
    showToast(d.message || 'Done', d.success ? 'rgba(0,200,100,0.9)' : 'rgba(255,60,60,0.9)');
    if (d.success) setTimeout(refreshData, 500);
    return d;
  }).catch(function(e) { showToast('Error: ' + e, 'rgba(255,60,60,0.9)'); });
}

/* ===== Phone Speaker (Server-generated Audio) ===== */

var autoSpeakTimer = null;
var phoneAudio = new Audio();

function playOnPhone(url) {
  phoneAudio.pause();
  phoneAudio.src = url + '?t=' + Date.now();
  phoneAudio.play().then(function() {
    showToast('Playing on phone speaker...', 'rgba(0,200,100,0.9)');
  }).catch(function(e) {
    showToast('Tap the page first, then try again (browser requires interaction)', 'rgba(255,60,60,0.9)');
  });
}

function browserSpeak() {
  playOnPhone('/api/speak_audio');
}

function testBrowserSpeak() {
  playOnPhone('/api/test_audio');
}

function toggleAutoSpeak() {
  if (autoSpeakTimer) {
    clearInterval(autoSpeakTimer);
    autoSpeakTimer = null;
    document.getElementById('autoSpeakBtn').textContent = 'Start Auto Speak';
    document.getElementById('autoSpeakBtn').className = 'btn btn-success';
    document.getElementById('autoSpeakStatus').style.display = 'none';
    showToast('Auto speak stopped', 'rgba(255,60,60,0.9)');
  } else {
    var interval = parseInt(document.getElementById('interval').value) || 60;
    document.getElementById('autoSpeakInterval').textContent = interval;
    browserSpeak();
    autoSpeakTimer = setInterval(browserSpeak, interval * 1000);
    document.getElementById('autoSpeakBtn').textContent = 'Stop Auto Speak';
    document.getElementById('autoSpeakBtn').className = 'btn btn-danger';
    document.getElementById('autoSpeakStatus').style.display = 'block';
    showToast('Auto speak started every ' + interval + 's', 'rgba(0,200,100,0.9)');
  }
}

function speakNow() { apiCall('/api/speak_now'); }
function testSpeak() { apiCall('/api/test'); }

function updateLangPreview() {
  var val = document.getElementById('googleLang').value;
  var parts = val.split('|');
  var langNames = {'en':'English','hi':'Hindi','mr':'Marathi','ta':'Tamil','te':'Telugu','kn':'Kannada'};
  document.getElementById('langPreview').textContent = 'Google TTS: ' + (langNames[parts[0]] || parts[0]) + ' voice';
}

function saveSettings() {
  var langVal = document.getElementById('googleLang').value.split('|');
  apiCall('/api/settings', 'POST', {
    speak_interval: parseInt(document.getElementById('interval').value),
    volume: parseInt(document.getElementById('volume').value),
    speed: parseInt(document.getElementById('speed').value),
    google_lang: langVal[0],
    google_tld: langVal[1],
    announce_location: document.getElementById('annLoc').checked,
    announce_value: document.getElementById('annVal').checked,
    announce_time: document.getElementById('annTime').checked
  }).then(function() { setTimeout(reloadSettings, 1000); });
}

function saveApiConfig() {
  apiCall('/api/api_config', 'POST', {
    unit_id: document.getElementById('unitId').value,
    username: document.getElementById('apiUser').value,
    password_auth: document.getElementById('apiPass').value
  }).then(function() { setTimeout(reloadSettings, 1000); });
}

/* ===== Bluetooth Functions ===== */

function btScan() {
  var btn = document.getElementById('scanBtn');
  var container = document.getElementById('btDevices');
  btn.disabled = true;
  btn.textContent = 'Scanning...';
  container.innerHTML = '<div class="bt-scanning"><span class="spinner"></span> Scanning for Bluetooth devices... (15s)</div>';

  fetch('/api/bt/scan', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      btn.disabled = false;
      btn.textContent = 'Scan for Devices';
      if (d.success) {
        renderBtDevices(d.devices);
      } else {
        container.innerHTML = '<div class="bt-empty">Scan failed: ' + (d.message || 'Unknown error') + '</div>';
      }
    })
    .catch(function(e) {
      btn.disabled = false;
      btn.textContent = 'Scan for Devices';
      container.innerHTML = '<div class="bt-empty">Scan error: ' + e + '</div>';
    });
}

function renderBtDevices(devices) {
  var container = document.getElementById('btDevices');
  if (!devices || devices.length === 0) {
    container.innerHTML = '<div class="bt-empty">No devices found. Make sure your speaker is in pairing mode.</div>';
    return;
  }

  var html = '';
  devices.forEach(function(dev) {
    var cls = 'bt-device';
    if (dev.connected) cls += ' connected';
    else if (dev.paired) cls += ' paired';

    var isAudio = dev.icon === 'audio-card' || dev.icon === 'audio-headset' || dev.icon === 'audio-headphones';

    html += '<div class="' + cls + '">';
    html += '  <div class="bt-info">';
    html += '    <div class="bt-name">' + dev.name + '</div>';
    html += '    <div class="bt-mac">' + dev.mac + '</div>';
    html += '    <div class="bt-tags">';
    if (dev.connected) html += '<span class="bt-tag bt-tag-connected">Connected</span>';
    if (dev.paired) html += '<span class="bt-tag bt-tag-paired">Paired</span>';
    if (isAudio) html += '<span class="bt-tag bt-tag-audio">Audio</span>';
    html += '    </div>';
    html += '  </div>';
    html += '  <div class="bt-actions">';

    if (dev.connected) {
      html += '<button class="btn btn-sm btn-danger" onclick="btDisconnect(\'' + dev.mac + '\')">Disconnect</button>';
    } else {
      html += '<button class="btn btn-sm btn-success" onclick="btConnect(\'' + dev.mac + '\')">Connect</button>';
    }
    if (dev.paired) {
      html += '<button class="btn btn-sm btn-warning" onclick="btRemove(\'' + dev.mac + '\')">Remove</button>';
    }

    html += '  </div>';
    html += '</div>';
  });

  container.innerHTML = html;
}

function btConnect(mac) {
  showToast('Connecting to ' + mac + '...', 'rgba(70,130,255,0.9)');
  fetch('/api/bt/connect', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mac: mac})
  }).then(function(r) { return r.json(); }).then(function(d) {
    showToast(d.message, d.success ? 'rgba(0,200,100,0.9)' : 'rgba(255,60,60,0.9)');
    if (d.success) {
      // Hide scan results and show connected device
      document.getElementById('btDevices').innerHTML = '';
      updateBtConnectedUI();
    }
    btRefreshDevices();
    setTimeout(refreshData, 1000);
  }).catch(function(e) { showToast('Error: ' + e, 'rgba(255,60,60,0.9)'); });
}

function btDisconnect(mac) {
  fetch('/api/bt/disconnect', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mac: mac})
  }).then(function(r) { return r.json(); }).then(function(d) {
    showToast(d.message, d.success ? 'rgba(0,200,100,0.9)' : 'rgba(255,60,60,0.9)');
    updateBtConnectedUI();
    btRefreshDevices();
    setTimeout(refreshData, 1000);
  }).catch(function(e) { showToast('Error: ' + e, 'rgba(255,60,60,0.9)'); });
}

function btDisconnectCurrent() {
  fetch('/api/bt/status').then(function(r) { return r.json(); }).then(function(d) {
    if (d.configured_device && d.configured_device.mac) {
      btDisconnect(d.configured_device.mac);
    }
  });
}

function updateBtConnectedUI() {
  fetch('/api/bt/status').then(function(r) { return r.json(); }).then(function(d) {
    var panel = document.getElementById('btConnected');
    if (d.connected_devices && d.connected_devices.length > 0) {
      var dev = d.connected_devices[0];
      document.getElementById('btConnName').textContent = dev.name;
      document.getElementById('btConnMac').textContent = dev.mac;
      panel.style.display = 'block';
    } else {
      panel.style.display = 'none';
    }
  });
}

function btRemove(mac) {
  if (!confirm('Remove and unpair this device?')) return;
  fetch('/api/bt/remove', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mac: mac})
  }).then(function(r) { return r.json(); }).then(function(d) {
    showToast(d.message, d.success ? 'rgba(0,200,100,0.9)' : 'rgba(255,60,60,0.9)');
    btRefreshDevices();
  }).catch(function(e) { showToast('Error: ' + e, 'rgba(255,60,60,0.9)'); });
}

function btRefreshDevices() {
  fetch('/api/bt/devices').then(function(r) { return r.json(); }).then(function(d) {
    if (d.success) renderBtDevices(d.devices);
  });
}

function setAudioOutput(mode) {
  apiCall('/api/audio_output', 'POST', { audio_output: mode });
}

function updateAudioOutputUI(mode) {
  ['Aux', 'Bt', 'Auto'].forEach(function(opt) {
    var el = document.getElementById('opt' + opt);
    el.classList.remove('active');
  });
  if (mode === 'aux') document.getElementById('optAux').classList.add('active');
  else if (mode === 'bluetooth') document.getElementById('optBt').classList.add('active');
  else document.getElementById('optAuto').classList.add('active');
}

/* ===== Data Refresh ===== */

var settingsLoaded = false;

function refreshData() {
  fetch('/api/status').then(function(r) { return r.json(); }).then(function(d) {
    // Always update live data
    document.getElementById('val').textContent = d.data.value.toFixed(1) + d.data.unit;
    document.getElementById('loc').textContent = d.data.location;
    document.getElementById('updated').textContent = d.data.last_update;

    var badge = document.getElementById('ttsStatus');
    if (d.tts_running) {
      badge.textContent = 'RUNNING'; badge.className = 'status-badge status-on';
    } else {
      badge.textContent = 'STOPPED'; badge.className = 'status-badge status-off';
    }

    // Audio status badge
    var audioBadge = document.getElementById('audioStatus');
    var ao = d.config.audio_output || 'aux';
    var btName = d.config.bt_device_name || '';
    if (ao === 'bluetooth' && btName) {
      audioBadge.textContent = 'BT: ' + btName;
      audioBadge.className = 'status-badge status-bt';
    } else if (ao === 'bluetooth') {
      audioBadge.textContent = 'BT (no device)';
      audioBadge.className = 'status-badge status-off';
    } else {
      audioBadge.textContent = ao.toUpperCase();
      audioBadge.className = 'status-badge status-on';
    }

    updateAudioOutputUI(ao);

    // Only load settings fields ONCE on page load (not on every refresh)
    if (!settingsLoaded) {
      settingsLoaded = true;
      var c = d.config;
      document.getElementById('interval').value = c.speak_interval;
      document.getElementById('volume').value = c.volume;
      document.getElementById('volVal').textContent = c.volume;
      document.getElementById('speed').value = c.speed;
      document.getElementById('spdVal').textContent = c.speed;
      var langKey = (c.google_lang || 'en') + '|' + (c.google_tld || 'co.in');
      document.getElementById('googleLang').value = langKey;
      updateLangPreview();
      document.getElementById('annLoc').checked = c.announce_location;
      document.getElementById('annVal').checked = c.announce_value;
      document.getElementById('annTime').checked = c.announce_time;
      document.getElementById('unitId').value = c.unit_id;
      document.getElementById('apiUser').value = c.username;
      document.getElementById('apiPass').value = c.password_auth;
    }
  });
}

function reloadSettings() {
  settingsLoaded = false;
  refreshData();
}

refreshData();
updateBtConnectedUI();
setInterval(refreshData, 10000);
setInterval(updateBtConnectedUI, 15000);
</script>
</body>
</html>"""

# ==================== API ROUTES ====================

@app.route("/")
def index():
    return HTML_PAGE


@app.route("/api/status")
def api_status():
    return jsonify({
        "success": True,
        "tts_running": tts_running,
        "data": last_data,
        "config": config
    })


@app.route("/api/start", methods=["POST"])
def api_start():
    if start_tts():
        config["enabled"] = True
        save_config()
        return jsonify({"success": True, "message": "TTS started"})
    return jsonify({"success": False, "message": "TTS already running"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_tts()
    config["enabled"] = False
    save_config()
    return jsonify({"success": True, "message": "TTS stopped"})


@app.route("/api/speak_now", methods=["POST"])
def api_speak_now():
    data = fetch_unit_data()
    if data:
        text = build_announcement(data)
        threading.Thread(target=speak, args=(text,), daemon=True).start()
        return jsonify({"success": True, "message": f"Speaking: {text}"})
    return jsonify({"success": False, "message": "No data available"})


@app.route("/api/test", methods=["POST"])
def api_test():
    threading.Thread(
        target=speak,
        args=("Aqua Box audio test. Speaker is working correctly.",),
        daemon=True
    ).start()
    return jsonify({"success": True, "message": "Playing test audio"})


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.get_json()
    for key in ["speak_interval", "volume", "speed", "voice", "tts_engine",
                "google_lang", "google_tld",
                "announce_location", "announce_value", "announce_time"]:
        if key in data:
            config[key] = data[key]
    save_config()
    return jsonify({"success": True, "message": "Settings saved"})


@app.route("/api/api_config", methods=["POST"])
def api_api_config():
    global token, token_expiry
    data = request.get_json()
    changed = False
    for key in ["unit_id", "username", "password_auth"]:
        if key in data and data[key]:
            config[key] = data[key]
            changed = True
    if changed:
        token = ""
        token_expiry = 0
        save_config()
    return jsonify({"success": True, "message": "API config saved. Token will refresh."})


@app.route("/api/announcement")
def api_announcement():
    """Get the current announcement text for browser TTS."""
    data = fetch_unit_data()
    if not data:
        data = last_data
    text = build_announcement(data)
    return jsonify({"success": True, "text": text, "data": data})


@app.route("/api/speak_audio")
def api_speak_audio():
    """Serve pre-cached announcement MP3 instantly, or generate on demand."""
    # Try cached version first (instant)
    if cached_speak_mp3 and os.path.exists(cached_speak_mp3):
        return send_file(cached_speak_mp3, mimetype="audio/mpeg")
    # Fallback: generate on demand
    text = build_announcement(last_data)
    mp3_path = "/tmp/aquabox_phone_speak.mp3"
    try:
        if generate_audio_mp3(text, mp3_path):
            return send_file(mp3_path, mimetype="audio/mpeg")
        return jsonify({"success": False, "message": "Audio generation failed"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/test_audio")
def api_test_audio():
    """Serve pre-cached test audio MP3."""
    test_path = os.path.join(CACHE_DIR, "test.mp3")
    if os.path.exists(test_path):
        return send_file(test_path, mimetype="audio/mpeg")
    # Generate if not cached
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        if generate_audio_mp3("Aqua Box audio test. Your phone speaker is working correctly.", test_path):
            return send_file(test_path, mimetype="audio/mpeg")
        return jsonify({"success": False, "message": "Audio generation failed"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/audio_output", methods=["POST"])
def api_audio_output():
    data = request.get_json()
    mode = data.get("audio_output", "auto")
    if mode in ("aux", "bluetooth", "auto"):
        config["audio_output"] = mode
        save_config()
        return jsonify({"success": True, "message": f"Audio output set to {mode}"})
    return jsonify({"success": False, "message": "Invalid audio output mode"})


# ==================== BLUETOOTH API ROUTES ====================

@app.route("/api/bt/scan", methods=["POST"])
def api_bt_scan():
    try:
        devices = bt_scan_devices()
        return jsonify({"success": True, "devices": devices, "message": f"Found {len(devices)} devices"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "devices": []})


@app.route("/api/bt/devices")
def api_bt_devices():
    return jsonify({"success": True, "devices": bt_scan_results})


@app.route("/api/bt/connect", methods=["POST"])
def api_bt_connect():
    data = request.get_json()
    mac = data.get("mac", "")
    if not mac:
        return jsonify({"success": False, "message": "No MAC address provided"})
    success, message = bt_pair_and_connect(mac)
    return jsonify({"success": success, "message": message})


@app.route("/api/bt/disconnect", methods=["POST"])
def api_bt_disconnect():
    data = request.get_json()
    mac = data.get("mac", "")
    if not mac:
        return jsonify({"success": False, "message": "No MAC address provided"})
    success, message = bt_disconnect(mac)
    return jsonify({"success": success, "message": message})


@app.route("/api/bt/remove", methods=["POST"])
def api_bt_remove():
    data = request.get_json()
    mac = data.get("mac", "")
    if not mac:
        return jsonify({"success": False, "message": "No MAC address provided"})
    success, message = bt_remove(mac)
    return jsonify({"success": success, "message": message})


@app.route("/api/bt/status")
def api_bt_status():
    status = bt_get_status()
    connected = bt_get_connected_audio()
    return jsonify({
        "success": True,
        "powered": status["powered"],
        "connected_devices": connected,
        "configured_device": {
            "mac": config.get("bt_device_mac", ""),
            "name": config.get("bt_device_name", ""),
        }
    })

# ==================== MAIN ====================

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Ensure print output is flushed immediately (important for nohup/redirect)
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    print("=" * 50)
    print("  AquaBox Text-to-Speech Service")
    print("=" * 50)

    load_config()
    print(f"  Unit ID : {config['unit_id']}")
    print(f"  Interval: {config['speak_interval']}s")
    print(f"  Volume  : {config['volume']}")
    print(f"  Speed   : {config['speed']} wpm")
    print(f"  Audio   : {config['audio_output']}")
    if config.get("bt_device_name"):
        print(f"  BT Dev  : {config['bt_device_name']} ({config['bt_device_mac']})")
    print("=" * 50)

    # Power on Bluetooth at startup
    print("  Initializing Bluetooth...")
    try:
        bt_power_on()
        bt_status = bt_get_status()
        print(f"  BT Power: {'ON' if bt_status['powered'] else 'OFF'}")
    except Exception as e:
        print(f"  BT Init error: {e}")

    # Auto-reconnect saved BT device
    if config.get("bt_device_mac") and config.get("audio_output") == "bluetooth":
        print(f"  Reconnecting to {config['bt_device_name']}...")
        try:
            output = bt_run(f"connect {config['bt_device_mac']}", timeout=10)
            time.sleep(3)
            info = bt_get_device_info(config["bt_device_mac"])
            if info["connected"]:
                print(f"  BT reconnected!")
            else:
                print(f"  BT reconnect failed, falling back to AUX")
        except Exception as e:
            print(f"  BT reconnect error: {e}")

    # Pre-generate test audio cache at startup
    print("  Pre-caching audio...")
    os.makedirs(CACHE_DIR, exist_ok=True)
    threading.Thread(
        target=generate_audio_mp3,
        args=("Aqua Box audio test. Your phone speaker is working correctly.",
              os.path.join(CACHE_DIR, "test.mp3")),
        daemon=True
    ).start()
    # Pre-fetch data and cache speak audio
    threading.Thread(target=lambda: (fetch_unit_data(), update_audio_cache()), daemon=True).start()

    # Auto-start TTS if enabled
    if config.get("enabled", True):
        start_tts()

    # Get IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "unknown"

    print(f"  Web UI  : http://{ip}:8080")
    print("=" * 50)

    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
