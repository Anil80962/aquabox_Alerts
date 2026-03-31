#!/usr/bin/env python3
"""
AquaBox WiFi Manager
- On boot: tries saved WiFi. If fails, starts AP hotspot "AquaBox-Setup".
- Web UI at http://192.168.4.1 (AP mode) or http://<pi-ip>:8090 (connected mode).
- Scan networks, connect, save credentials.
- Runs as systemd service on boot.
"""

import os
import sys
import json
import time
import re
import subprocess
import threading
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifi_config.json")
AP_SSID = "AquaBox-Setup"
AP_PASSWORD = "aquabox123"
AP_IP = "192.168.4.1"
WEB_PORT = 80  # Port 80 in AP mode so captive portal works
CONNECTED_PORT = 8090  # Port when connected to WiFi
WIFI_TIMEOUT = 20  # Seconds to wait for WiFi connection
INTERFACE = "wlan0"

is_ap_mode = False
current_port = WEB_PORT

# ==================== WiFi Functions ====================

def run_cmd(cmd, timeout=15):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "timeout", 1
    except Exception as e:
        return str(e), 1


def get_current_ssid():
    """Get currently connected WiFi SSID."""
    out, _ = run_cmd("iwgetid -r")
    return out


def get_current_ip():
    """Get current IP address."""
    out, _ = run_cmd(f"ip -4 addr show {INTERFACE} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}'")
    return out.split("\n")[0] if out else ""


def is_wifi_connected():
    """Check if WiFi is connected."""
    ssid = get_current_ssid()
    ip = get_current_ip()
    return bool(ssid and ip and ip != AP_IP)


def scan_wifi():
    """Scan for available WiFi networks."""
    run_cmd(f"nmcli dev wifi rescan ifname {INTERFACE}", timeout=10)
    time.sleep(3)
    out, _ = run_cmd("nmcli -t -f SSID,SIGNAL,SECURITY,IN-USE dev wifi list --rescan no")
    networks = []
    seen = set()
    for line in out.split("\n"):
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 3:
            ssid = parts[0].replace("\\:", ":")
            signal = parts[1] if len(parts) > 1 else "0"
            security = parts[2] if len(parts) > 2 else ""
            active = parts[3] == "*" if len(parts) > 3 else False
            if ssid and ssid not in seen:
                seen.add(ssid)
                networks.append({
                    "ssid": ssid,
                    "signal": int(signal) if signal.isdigit() else 0,
                    "security": security,
                    "active": active
                })
    networks.sort(key=lambda x: (-x["active"], -x["signal"]))
    return networks


def connect_wifi(ssid, password):
    """Connect to a WiFi network using nmcli."""
    print(f"[WiFi] Connecting to '{ssid}'...")

    # Delete existing connection for this SSID if any
    run_cmd(f'nmcli con delete id "{ssid}" 2>/dev/null')
    time.sleep(1)

    # Connect
    if password:
        out, rc = run_cmd(
            f'nmcli dev wifi connect "{ssid}" password "{password}" ifname {INTERFACE}',
            timeout=30
        )
    else:
        out, rc = run_cmd(
            f'nmcli dev wifi connect "{ssid}" ifname {INTERFACE}',
            timeout=30
        )

    time.sleep(3)

    if rc == 0 or is_wifi_connected():
        ip = get_current_ip()
        print(f"[WiFi] Connected to '{ssid}' with IP: {ip}")
        save_wifi_config(ssid, password)
        return True, ip
    else:
        print(f"[WiFi] Failed to connect: {out}")
        return False, out


def disconnect_wifi():
    """Disconnect from current WiFi."""
    run_cmd(f"nmcli dev disconnect {INTERFACE}")


def save_wifi_config(ssid, password):
    """Save WiFi credentials."""
    cfg = load_wifi_config()
    cfg["ssid"] = ssid
    cfg["password"] = password
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[WiFi] Save config error: {e}")


def load_wifi_config():
    """Load saved WiFi config."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ssid": "", "password": ""}


# ==================== AP Hotspot Functions ====================

def start_ap():
    """Start Access Point hotspot."""
    global is_ap_mode
    print(f"[AP] Starting hotspot '{AP_SSID}'...")

    # Stop any existing connections
    run_cmd(f"nmcli dev disconnect {INTERFACE}", timeout=5)
    time.sleep(1)

    # Delete old AP connection if exists
    run_cmd(f'nmcli con delete "{AP_SSID}" 2>/dev/null')
    time.sleep(1)

    # Create AP hotspot
    out, rc = run_cmd(
        f'nmcli con add type wifi ifname {INTERFACE} con-name "{AP_SSID}" '
        f'autoconnect no ssid "{AP_SSID}" -- '
        f'wifi.mode ap wifi.band bg wifi.channel 6 '
        f'ipv4.method shared ipv4.addresses {AP_IP}/24 '
        f'wifi-sec.key-mgmt wpa-psk wifi-sec.psk "{AP_PASSWORD}"',
        timeout=10
    )
    print(f"[AP] Create result: {out}")

    # Activate AP
    out, rc = run_cmd(f'nmcli con up "{AP_SSID}"', timeout=10)
    print(f"[AP] Activate result: {out}")
    time.sleep(3)

    is_ap_mode = True
    print(f"[AP] Hotspot active! SSID: {AP_SSID}, Password: {AP_PASSWORD}")
    print(f"[AP] Web UI: http://{AP_IP}")


def stop_ap():
    """Stop Access Point hotspot."""
    global is_ap_mode
    print("[AP] Stopping hotspot...")
    run_cmd(f'nmcli con down "{AP_SSID}"', timeout=5)
    run_cmd(f'nmcli con delete "{AP_SSID}"', timeout=5)
    is_ap_mode = False
    time.sleep(2)


def try_saved_wifi():
    """Try connecting to saved WiFi. Returns True if connected."""
    cfg = load_wifi_config()
    if cfg.get("ssid"):
        print(f"[WiFi] Trying saved network: {cfg['ssid']}")
        success, _ = connect_wifi(cfg["ssid"], cfg.get("password", ""))
        if success:
            return True

    # Also check if already connected via NetworkManager
    if is_wifi_connected():
        print(f"[WiFi] Already connected to: {get_current_ssid()}")
        return True

    return False


# ==================== Web UI ====================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>AquaBox WiFi Setup</title>
<style>
  :root { --primary: #0ea5e9; --success: #10b981; --danger: #ef4444; --warning: #f59e0b; --bg: #0b1120; --card: rgba(15,23,42,0.85); --border: rgba(255,255,255,0.06); --text: #e2e8f0; --muted: #64748b; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); min-height: 100vh; color: var(--text); }
  body::before { content:''; position:fixed; top:0; left:0; right:0; bottom:0; background: radial-gradient(ellipse at 20% 50%, rgba(14,165,233,0.08) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(16,185,129,0.06) 0%, transparent 50%); pointer-events:none; z-index:0; }
  .container { max-width: 460px; margin: 0 auto; padding: 16px; position: relative; z-index: 1; }

  /* Header */
  .header { text-align: center; padding: 20px 0 16px; }
  .header-icon { width: 48px; height: 48px; background: linear-gradient(135deg, var(--primary), #06b6d4); border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 10px; box-shadow: 0 8px 24px rgba(14,165,233,0.25); }
  .header-icon svg { width: 26px; height: 26px; fill: #fff; }
  .header h1 { font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }
  .header p { font-size: 12px; color: var(--muted); margin-top: 2px; }

  /* Cards */
  .card { background: var(--card); backdrop-filter: blur(16px); border-radius: 16px; padding: 20px; margin-bottom: 12px; border: 1px solid var(--border); box-shadow: 0 4px 24px rgba(0,0,0,0.2); }
  .card-title { font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
  .card-title svg { width: 16px; height: 16px; fill: var(--primary); flex-shrink: 0; }

  /* Status Banner */
  .status-banner { display: flex; align-items: center; gap: 14px; padding: 16px; border-radius: 12px; }
  .status-banner.online { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.15); }
  .status-banner.offline { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.15); }
  .status-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .status-banner.online .status-icon { background: rgba(16,185,129,0.15); }
  .status-banner.offline .status-icon { background: rgba(245,158,11,0.15); }
  .status-icon svg { width: 22px; height: 22px; }
  .status-banner.online .status-icon svg { fill: var(--success); }
  .status-banner.offline .status-icon svg { fill: var(--warning); }
  .status-info { flex: 1; min-width: 0; }
  .status-info .name { font-size: 16px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .status-banner.online .name { color: var(--success); }
  .status-banner.offline .name { color: var(--warning); }
  .status-info .meta { font-size: 12px; color: var(--muted); margin-top: 2px; display: flex; gap: 12px; flex-wrap: wrap; }
  .meta-item { display: flex; align-items: center; gap: 4px; }
  .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
  .dot-green { background: var(--success); box-shadow: 0 0 6px var(--success); }
  .dot-orange { background: var(--warning); box-shadow: 0 0 6px var(--warning); }

  /* Signal SVG bars */
  .signal-bars { display: inline-flex; align-items: flex-end; gap: 2px; height: 18px; }
  .signal-bars .bar { width: 4px; border-radius: 1.5px; background: rgba(255,255,255,0.12); transition: background 0.3s; }
  .signal-bars .bar.active { background: var(--success); }
  .signal-bars .bar:nth-child(1) { height: 5px; }
  .signal-bars .bar:nth-child(2) { height: 9px; }
  .signal-bars .bar:nth-child(3) { height: 13px; }
  .signal-bars .bar:nth-child(4) { height: 18px; }
  .signal-bars.weak .bar:nth-child(1) { background: var(--danger); }
  .signal-bars.fair .bar:nth-child(1), .signal-bars.fair .bar:nth-child(2) { background: var(--warning); }
  .signal-bars.good .bar:nth-child(1), .signal-bars.good .bar:nth-child(2), .signal-bars.good .bar:nth-child(3) { background: var(--success); }
  .signal-bars.excellent .bar { background: var(--success); }

  /* WiFi List */
  .wifi-list { list-style: none; }
  .wifi-item {
    display: flex; align-items: center; gap: 12px;
    padding: 13px 14px; margin-bottom: 6px; border-radius: 12px;
    background: rgba(255,255,255,0.02); border: 1px solid var(--border);
    cursor: pointer; transition: all 0.15s ease;
  }
  .wifi-item:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.12); transform: translateY(-1px); }
  .wifi-item:active { transform: scale(0.985); }
  .wifi-item.active { background: rgba(16,185,129,0.06); border-color: rgba(16,185,129,0.2); }
  .wifi-icon { width: 36px; height: 36px; border-radius: 10px; background: rgba(14,165,233,0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .wifi-item.active .wifi-icon { background: rgba(16,185,129,0.12); }
  .wifi-icon svg { width: 18px; height: 18px; fill: var(--primary); }
  .wifi-item.active .wifi-icon svg { fill: var(--success); }
  .wifi-info { flex: 1; min-width: 0; }
  .wifi-name { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .wifi-meta { font-size: 11px; color: var(--muted); margin-top: 2px; display: flex; align-items: center; gap: 6px; }
  .wifi-badge { font-size: 9px; padding: 2px 6px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
  .badge-secure { background: rgba(14,165,233,0.12); color: var(--primary); }
  .badge-open { background: rgba(245,158,11,0.12); color: var(--warning); }
  .badge-connected { background: rgba(16,185,129,0.12); color: var(--success); }
  .wifi-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .wifi-empty { text-align: center; padding: 30px 16px; color: var(--muted); font-size: 13px; }

  /* Inputs */
  label { display: block; font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; margin-top: 16px; }
  input[type=text], input[type=password] {
    width: 100%; padding: 12px 14px; border-radius: 10px;
    border: 1px solid var(--border); background: rgba(255,255,255,0.04);
    color: var(--text); font-size: 15px; outline: none; transition: border 0.2s;
  }
  input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(14,165,233,0.1); }
  .pass-wrap { position: relative; }
  .toggle-pass { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--muted); font-size: 12px; cursor: pointer; font-weight: 600; }

  /* Buttons */
  .btn { width: 100%; padding: 13px; border: none; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 14px; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }
  .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
  .btn:active { transform: scale(0.98); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; box-shadow: none; }
  .btn-primary { background: linear-gradient(135deg, var(--primary), #0284c7); color: #fff; }
  .btn-scan { background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; }
  .btn svg { width: 16px; height: 16px; fill: currentColor; }

  /* Toast */
  .toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(100px); padding: 12px 22px; border-radius: 12px; font-size: 13px; font-weight: 500; color: #fff; z-index: 100; max-width: 90%; text-align: center; transition: transform 0.3s cubic-bezier(0.175,0.885,0.32,1.275); backdrop-filter: blur(8px); }
  .toast.show { transform: translateX(-50%) translateY(0); }

  /* Spinner */
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.2); border-top-color: currentColor; border-radius: 50%; animation: spin 0.7s linear infinite; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes fadeIn { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: translateY(0); } }
  .wifi-item { animation: fadeIn 0.3s ease both; }
  .wifi-item:nth-child(2) { animation-delay: 0.05s; }
  .wifi-item:nth-child(3) { animation-delay: 0.1s; }
  .wifi-item:nth-child(4) { animation-delay: 0.15s; }
  .wifi-item:nth-child(5) { animation-delay: 0.2s; }

  .connect-form { display: none; }
  .connect-form.show { display: block; animation: fadeIn 0.3s ease; }
  .divider { height: 1px; background: var(--border); margin: 16px 0; }
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <div class="header-icon">
      <svg viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
    </div>
    <h1>AquaBox WiFi</h1>
    <p>Network Configuration</p>
  </div>

  <!-- Status -->
  <div class="card">
    <div id="statusBanner" class="status-banner offline">
      <div class="status-icon">
        <svg viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
      </div>
      <div class="status-info">
        <div class="name" id="statusName">Checking...</div>
        <div class="meta" id="statusMeta"></div>
      </div>
      <div id="statusSignal"></div>
    </div>
  </div>

  <!-- WiFi Networks -->
  <div class="card">
    <div class="card-title">
      <svg viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
      Available Networks
    </div>
    <button class="btn btn-scan" id="scanBtn" onclick="scanWifi()">
      <svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
      Scan Networks
    </button>
    <ul class="wifi-list" id="wifiList" style="margin-top: 14px;">
      <li class="wifi-empty">Tap "Scan Networks" to discover nearby WiFi</li>
    </ul>
  </div>

  <!-- Connect Form (hidden by default) -->
  <div class="card connect-form" id="connectForm">
    <div class="card-title">
      <svg viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg>
      Connect to Network
    </div>
    <label>Network Name</label>
    <input type="text" id="ssidInput" readonly style="background:rgba(14,165,233,0.06);">
    <label>Password</label>
    <div class="pass-wrap">
      <input type="password" id="passInput" placeholder="Enter WiFi password">
      <button class="toggle-pass" onclick="togglePass()">Show</button>
    </div>
    <button class="btn btn-primary" id="connectBtn" onclick="connectWifi()">
      <svg viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
      Connect
    </button>
  </div>

  <!-- Manual Connect -->
  <div class="card">
    <div class="card-title">
      <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
      Manual Entry
    </div>
    <label>WiFi Name (SSID)</label>
    <input type="text" id="manualSsid" placeholder="Enter network name">
    <label>Password</label>
    <div class="pass-wrap">
      <input type="password" id="manualPass" placeholder="Enter password (leave empty if open)">
      <button class="toggle-pass" onclick="toggleManualPass()">Show</button>
    </div>
    <button class="btn btn-primary" onclick="connectManual()">
      <svg viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
      Connect
    </button>
  </div>

  <div style="text-align:center; padding:12px; font-size:11px; color:var(--muted);">AquaBox WiFi Manager v1.0 &middot; Fluxgen</div>
</div>

<div class="toast" id="toast"></div>

<script>
function showToast(msg, bg) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = bg || 'rgba(16,185,129,0.9)';
  t.className = 'toast show';
  setTimeout(function() { t.className = 'toast'; }, 4000);
}

function signalBarsHTML(strength) {
  var s = parseInt(strength) || 0;
  var cls = 'signal-bars';
  if (s >= 70) cls += ' excellent';
  else if (s >= 50) cls += ' good';
  else if (s >= 30) cls += ' fair';
  else cls += ' weak';
  var bars = '';
  for (var i = 0; i < 4; i++) {
    var threshold = [1, 30, 50, 70];
    bars += '<div class="bar' + (s >= threshold[i] ? ' active' : '') + '"></div>';
  }
  return '<div class="' + cls + '">' + bars + '</div>';
}

function scanWifi() {
  var btn = document.getElementById('scanBtn');
  var list = document.getElementById('wifiList');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Scanning...';
  list.innerHTML = '<li class="wifi-empty"><span class="spinner"></span> Discovering networks...</li>';

  fetch('/api/scan', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      btn.disabled = false;
      btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg> Scan Networks';
      if (d.networks && d.networks.length > 0) {
        var html = '';
        d.networks.forEach(function(n) {
          var cls = n.active ? 'wifi-item active' : 'wifi-item';
          var secBadge = n.security ? '<span class="wifi-badge badge-secure">Secured</span>' : '<span class="wifi-badge badge-open">Open</span>';
          var connBadge = n.active ? '<span class="wifi-badge badge-connected">Connected</span>' : '';
          html += '<li class="' + cls + '" onclick="selectWifi(\'' + n.ssid.replace(/'/g, "\\'") + '\')">';
          html += '<div class="wifi-icon"><svg viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg></div>';
          html += '<div class="wifi-info"><div class="wifi-name">' + n.ssid + '</div>';
          html += '<div class="wifi-meta">' + secBadge + connBadge + ' ' + n.signal + '%</div></div>';
          html += '<div class="wifi-right">' + signalBarsHTML(n.signal) + '</div>';
          html += '</li>';
        });
        list.innerHTML = html;
      } else {
        list.innerHTML = '<li class="wifi-empty">No networks found. Move closer to router and try again.</li>';
      }
    })
    .catch(function(e) {
      btn.disabled = false;
      btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg> Scan Networks';
      list.innerHTML = '<li class="wifi-empty">Scan failed. Please try again.</li>';
    });
}

function selectWifi(ssid) {
  document.getElementById('ssidInput').value = ssid;
  document.getElementById('passInput').value = '';
  document.getElementById('connectForm').className = 'card connect-form show';
  document.getElementById('passInput').focus();
  document.getElementById('connectForm').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function connectWifi() {
  var ssid = document.getElementById('ssidInput').value;
  var pass = document.getElementById('passInput').value;
  doConnect(ssid, pass);
}

function connectManual() {
  var ssid = document.getElementById('manualSsid').value.trim();
  var pass = document.getElementById('manualPass').value;
  if (!ssid) { showToast('Please enter a network name', 'rgba(239,68,68,0.9)'); return; }
  doConnect(ssid, pass);
}

function doConnect(ssid, pass) {
  showToast('Connecting to ' + ssid + '...', 'rgba(99,102,241,0.9)');
  fetch('/api/connect', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ssid: ssid, password: pass})
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.success) {
      showToast('Connected to ' + ssid + '! IP: ' + d.ip, 'rgba(16,185,129,0.9)');
      document.getElementById('connectForm').className = 'card connect-form';
      setTimeout(refreshStatus, 2000);
      if (d.ip) {
        setTimeout(function() { window.location.href = 'http://' + d.ip + ':8090'; }, 5000);
      }
    } else {
      showToast('Connection failed: ' + d.message, 'rgba(239,68,68,0.9)');
    }
  })
  .catch(function() {
    showToast('Connection lost. Connect to new WiFi network.', 'rgba(245,158,11,0.9)');
  });
}

function refreshStatus() {
  fetch('/api/status')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var banner = document.getElementById('statusBanner');
      var name = document.getElementById('statusName');
      var meta = document.getElementById('statusMeta');
      var sig = document.getElementById('statusSignal');

      if (d.ap_mode) {
        banner.className = 'status-banner offline';
        name.textContent = 'Hotspot Active';
        meta.innerHTML = '<span class="meta-item"><span class="dot dot-orange"></span> ' + d.ap_ssid + '</span><span class="meta-item">Password: aquabox123</span>';
        sig.innerHTML = '';
      } else if (d.connected) {
        banner.className = 'status-banner online';
        name.textContent = d.ssid;
        var sigVal = parseInt(d.signal) || 0;
        // Convert dBm to percentage if negative
        if (sigVal < 0) sigVal = Math.min(100, Math.max(0, 2 * (sigVal + 100)));
        meta.innerHTML = '<span class="meta-item"><span class="dot dot-green"></span> Connected</span><span class="meta-item">IP: ' + d.ip + '</span>';
        sig.innerHTML = signalBarsHTML(sigVal);
      } else {
        banner.className = 'status-banner offline';
        name.textContent = 'Disconnected';
        meta.innerHTML = '<span class="meta-item"><span class="dot dot-orange"></span> No network</span>';
        sig.innerHTML = '';
      }
    })
    .catch(function() {});
}

function togglePass() {
  var p = document.getElementById('passInput'); var b = p.nextElementSibling;
  if (p.type === 'password') { p.type = 'text'; b.textContent = 'Hide'; } else { p.type = 'password'; b.textContent = 'Show'; }
}
function toggleManualPass() {
  var p = document.getElementById('manualPass'); var b = p.nextElementSibling;
  if (p.type === 'password') { p.type = 'text'; b.textContent = 'Hide'; } else { p.type = 'password'; b.textContent = 'Show'; }
}

refreshStatus();
setInterval(refreshStatus, 10000);
</script>
</body>
</html>"""

# ==================== API Routes ====================

@app.route("/")
def index():
    return HTML_PAGE


@app.route("/generate_204")
@app.route("/hotspot-detect.html")
@app.route("/fwlink")
@app.route("/connecttest.txt")
@app.route("/redirect")
@app.route("/success.txt")
def captive_portal():
    """Handle captive portal detection from Android/iOS/Windows."""
    return redirect("/", code=302)


@app.route("/api/status")
def api_status():
    ssid = get_current_ssid()
    ip = get_current_ip()
    connected = is_wifi_connected()
    signal = ""
    if connected:
        out, _ = run_cmd(f"iwconfig {INTERFACE} | grep -oP 'Signal level=\\K[^ ]+'")
        signal = out

    return jsonify({
        "connected": connected,
        "ssid": ssid,
        "ip": ip,
        "signal": signal,
        "ap_mode": is_ap_mode,
        "ap_ssid": AP_SSID
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    try:
        networks = scan_wifi()
        return jsonify({"success": True, "networks": networks})
    except Exception as e:
        return jsonify({"success": False, "networks": [], "message": str(e)})


@app.route("/api/connect", methods=["POST"])
def api_connect():
    data = request.get_json()
    ssid = data.get("ssid", "").strip()
    password = data.get("password", "")

    if not ssid:
        return jsonify({"success": False, "message": "SSID required"})

    # If in AP mode, stop AP first
    if is_ap_mode:
        stop_ap()
        time.sleep(2)

    success, result = connect_wifi(ssid, password)

    if success:
        # Schedule restart of web server on new port after response
        def restart_on_connected_port():
            time.sleep(3)
            print(f"[WiFi] Connected! Access web UI at http://{result}:{CONNECTED_PORT}")
        threading.Thread(target=restart_on_connected_port, daemon=True).start()
        return jsonify({"success": True, "ip": result, "message": f"Connected to {ssid}"})
    else:
        # Connection failed, restart AP
        if not is_wifi_connected():
            threading.Thread(target=start_ap, daemon=True).start()
        return jsonify({"success": False, "message": result or "Connection failed"})


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    disconnect_wifi()
    time.sleep(2)
    if not is_wifi_connected():
        threading.Thread(target=start_ap, daemon=True).start()
    return jsonify({"success": True, "message": "Disconnected"})


@app.route("/api/saved")
def api_saved():
    cfg = load_wifi_config()
    return jsonify({"ssid": cfg.get("ssid", ""), "has_password": bool(cfg.get("password"))})


# ==================== Main ====================

def startup():
    """Startup logic: try WiFi, fallback to AP."""
    global is_ap_mode, current_port

    print("=" * 50)
    print("  AquaBox WiFi Manager")
    print("=" * 50)

    # Try connecting to saved WiFi
    if try_saved_wifi():
        print(f"[WiFi] Connected to: {get_current_ssid()}")
        print(f"[WiFi] IP: {get_current_ip()}")
        is_ap_mode = False
        current_port = CONNECTED_PORT
    else:
        print("[WiFi] No saved WiFi or connection failed.")
        print("[WiFi] Starting Access Point hotspot...")
        start_ap()
        current_port = WEB_PORT

    print(f"  Web UI port: {current_port}")
    print("=" * 50)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    startup()

    # Run on both ports if connected (for compatibility)
    if is_ap_mode:
        print(f"[AP] Web server on http://{AP_IP}:{WEB_PORT}")
        app.run(host="0.0.0.0", port=WEB_PORT, debug=False, use_reloader=False)
    else:
        ip = get_current_ip()
        print(f"[WiFi] Web server on http://{ip}:{CONNECTED_PORT}")
        app.run(host="0.0.0.0", port=CONNECTED_PORT, debug=False, use_reloader=False)
