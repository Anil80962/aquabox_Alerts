#!/usr/bin/env python3
"""
AquaBox Alerts Display
- Fetches bearer token from AquaGen API
- Fetches daily alerts
- Displays alerts on the 5-inch HDMI screen via GTK
- Auto-refreshes every 60 seconds
- Scrollable alert cards with color-coded importance
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf
import cairo, math as _math, random as _random
import requests
import json
import time
import threading
import signal
import sys
import os
from datetime import datetime

# ==================== CONFIG ====================
AUTH_URL = "https://prod-aquagen.azurewebsites.net/api/user/user/login?format=v1"
ALERTS_URL = "https://prod-aquagen.azurewebsites.net/api/user/alerts"
MARK_READ_URL = "https://prod-aquagen.azurewebsites.net/api/user/notification/updateRead"
USERNAME = ""
PASSWORD = ""
LOGIN_TYPE = "DEFAULT"
TTS_LANG = "en"  # en=English, te=Telugu, hi=Hindi, kn=Kannada, ta=Tamil

# Translations for TTS announcements
TRANSLATIONS = {
    "en": {
        "alert": "Alert",
        "of": "of",
        "unread_alert": "Unread alert",
        "offline_unit": "Offline unit",
        "filled": "filled",
        "stock_upper": "Stock Level Upper limit reached",
        "stock_lower": "Stock Level Lower limit reached",
        "daily_limit": "Daily Limit Reached",
        "daily_limit_90": "90 percent of the Daily Limit Reached",
        "abnormal": "Abnormal water usage detected",
        "offline": "Device is offline",
        "online": "Device is back online",
        "at": "at",
        "current_stock": "Current Stock",
        "upper_limit": "Upper Limit",
        "lower_limit": "Lower Limit",
    },
    "te": {
        "alert": "హెచ్చరిక",
        "of": "లో",
        "unread_alert": "చదవని హెచ్చరిక",
        "offline_unit": "ఆఫ్‌లైన్ యూనిట్",
        "filled": "నిండింది",
        "stock_upper": "నీటి మట్టం పై పరిమితి చేరుకుంది",
        "stock_lower": "నీటి మట్టం కింది పరిమితి చేరుకుంది",
        "daily_limit": "రోజువారీ పరిమితి చేరుకుంది",
        "daily_limit_90": "రోజువారీ పరిమితిలో 90 శాతం చేరుకుంది",
        "abnormal": "అసాధారణ నీటి వినియోగం గుర్తించబడింది",
        "offline": "పరికరం ఆఫ్‌లైన్‌లో ఉంది",
        "online": "పరికరం తిరిగి ఆన్‌లైన్‌లో ఉంది",
        "at": "సమయం",
        "current_stock": "ప్రస్తుత నిల్వ",
        "upper_limit": "పై పరిమితి",
        "lower_limit": "కింది పరిమితి",
    },
    "hi": {
        "alert": "चेतावनी",
        "of": "में से",
        "unread_alert": "अपठित चेतावनी",
        "offline_unit": "ऑफलाइन यूनिट",
        "filled": "भरा हुआ",
        "stock_upper": "जल स्तर ऊपरी सीमा पर पहुंच गया",
        "stock_lower": "जल स्तर निचली सीमा पर पहुंच गया",
        "daily_limit": "दैनिक सीमा पूरी हो गई",
        "daily_limit_90": "दैनिक सीमा का 90 प्रतिशत पूरा हो गया",
        "abnormal": "असामान्य पानी का उपयोग पाया गया",
        "offline": "डिवाइस ऑफलाइन है",
        "online": "डिवाइस वापस ऑनलाइन है",
        "at": "बजे",
        "current_stock": "वर्तमान स्टॉक",
        "upper_limit": "ऊपरी सीमा",
        "lower_limit": "निचली सीमा",
    },
    "kn": {
        "alert": "ಎಚ್ಚರಿಕೆ",
        "of": "ರಲ್ಲಿ",
        "unread_alert": "ಓದದ ಎಚ್ಚರಿಕೆ",
        "offline_unit": "ಆಫ್‌ಲೈನ್ ಘಟಕ",
        "filled": "ತುಂಬಿದೆ",
        "stock_upper": "ನೀರಿನ ಮಟ್ಟ ಮೇಲಿನ ಮಿತಿ ತಲುಪಿದೆ",
        "stock_lower": "ನೀರಿನ ಮಟ್ಟ ಕೆಳಗಿನ ಮಿತಿ ತಲುಪಿದೆ",
        "daily_limit": "ದೈನಂದಿನ ಮಿತಿ ತಲುಪಿದೆ",
        "daily_limit_90": "ದೈನಂದಿನ ಮಿತಿಯ 90 ಶೇಕಡಾ ತಲುಪಿದೆ",
        "abnormal": "ಅಸಹಜ ನೀರಿನ ಬಳಕೆ ಪತ್ತೆಯಾಗಿದೆ",
        "offline": "ಸಾಧನ ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿದೆ",
        "online": "ಸಾಧನ ಮತ್ತೆ ಆನ್‌ಲೈನ್‌ನಲ್ಲಿದೆ",
        "at": "ಸಮಯ",
        "current_stock": "ಪ್ರಸ್ತುತ ದಾಸ್ತಾನು",
        "upper_limit": "ಮೇಲಿನ ಮಿತಿ",
        "lower_limit": "ಕೆಳಗಿನ ಮಿತಿ",
    },
    "ml": {
        "alert": "മുന്നറിയിപ്പ്",
        "of": "ൽ",
        "unread_alert": "വായിക്കാത്ത മുന്നറിയിപ്പ്",
        "offline_unit": "ഓഫ്‌ലൈൻ യൂണിറ്റ്",
        "filled": "നിറഞ്ഞു",
        "stock_upper": "ജല നിരപ്പ് ഉയർന്ന പരിധി എത്തി",
        "stock_lower": "ജല നിരപ്പ് താഴ്ന്ന പരിധി എത്തി",
        "daily_limit": "ദൈനംദിന പരിധി എത്തി",
        "daily_limit_90": "ദൈനംദിന പരിധിയുടെ 90 ശതമാനം എത്തി",
        "abnormal": "അസാധാരണ ജല ഉപയോഗം കണ്ടെത്തി",
        "offline": "ഉപകരണം ഓഫ്‌ലൈനിലാണ്",
        "online": "ഉപകരണം വീണ്ടും ഓൺലൈനിലാണ്",
        "at": "സമയം",
        "current_stock": "നിലവിലെ സ്റ്റോക്ക്",
        "upper_limit": "ഉയർന്ന പരിധി",
        "lower_limit": "താഴ്ന്ന പരിധി",
    },
    "ta": {
        "alert": "எச்சரிக்கை",
        "of": "இல்",
        "unread_alert": "படிக்காத எச்சரிக்கை",
        "offline_unit": "ஆஃப்லைன் அலகு",
        "filled": "நிரம்பியது",
        "stock_upper": "நீர் மட்டம் மேல் வரம்பை எட்டியது",
        "stock_lower": "நீர் மட்டம் கீழ் வரம்பை எட்டியது",
        "daily_limit": "தினசரி வரம்பு எட்டியது",
        "daily_limit_90": "தினசரி வரம்பின் 90 சதவீதம் எட்டியது",
        "abnormal": "அசாதாரண நீர் பயன்பாடு கண்டறியப்பட்டது",
        "offline": "சாதனம் ஆஃப்லைனில் உள்ளது",
        "online": "சாதனம் மீண்டும் ஆன்லைனில் உள்ளது",
        "at": "நேரம்",
        "current_stock": "தற்போதைய இருப்பு",
        "upper_limit": "மேல் வரம்பு",
        "lower_limit": "கீழ் வரம்பு",
    },
}


def translate_alert_text(title, body, status, lang):
    """Translate alert text to local language, keep location name in English."""
    t = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    # Body translations
    translated_body = body
    if "filled" in body.lower():
        # Extract percentage e.g. "90.84% filled"
        parts = body.split("%")
        if len(parts) > 1:
            translated_body = parts[0] + "% " + t["filled"]
        else:
            translated_body = body.replace("filled", t["filled"])
    elif "Daily Limit Reached" in body:
        translated_body = t["daily_limit"]
    elif "90% of the Daily Limit" in body:
        translated_body = t["daily_limit_90"]
    elif "Abnormal" in body:
        translated_body = t["abnormal"]
    elif body.lower() == "offline":
        translated_body = t["offline"]
    elif body.lower() == "online":
        translated_body = t["online"]

    # Status translations
    translated_status = status
    if "Upper limit reached" in status:
        time_part = status.split("at")[-1].strip() if "at" in status else ""
        translated_status = t["stock_upper"] + (" " + t["at"] + " " + time_part if time_part else "")
    elif "Lower limit reached" in status:
        time_part = status.split("at")[-1].strip() if "at" in status else ""
        translated_status = t["stock_lower"] + (" " + t["at"] + " " + time_part if time_part else "")
    elif "daily consumption limit reached" in status.lower():
        time_part = status.split("at")[-1].strip() if "at" in status else ""
        translated_status = t["daily_limit"] + (" " + t["at"] + " " + time_part if time_part else "")
    elif "90%" in status and "limit" in status.lower():
        translated_status = t["daily_limit_90"]
    elif "Abnormal" in status:
        translated_status = t["abnormal"]
    elif "offline" in status.lower():
        translated_status = t["offline"]
    elif "online" in status.lower():
        translated_status = t["online"]

    # Title stays in English (location name)
    return title, translated_body, translated_status


LOGGED_IN = False
CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_session.json")
ADMIN_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_config.json")
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
REFRESH_INTERVAL = 120  # seconds (2 minutes)
OFFLINE_ANNOUNCE_INTERVAL = 3600  # 1 hour auto-announce offline  # seconds (2 minutes)
TOKEN_REFRESH = 13800  # refresh token every 3hr 50min (10 min before 4hr expiry)
AUTO_MARK_READ = True  # Auto mark alerts as read when displayed
ANNOUNCED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "announced_alerts.json")

# ==================== GLOBALS ====================
token = ""
token_time = 0
alerts_data = {}
fetch_lock = threading.Lock()
announced_ids = set()  # Track announced alert IDs to avoid repeats
_announce_stop = False  # Flag to stop announcing
_announced_ids = set()  # Track already-announced alert IDs
_auto_announcing = False  # Prevent overlapping auto-announce
_refresh_queued = False  # Queue refresh if announce is running
# No lock needed - _announce_stop handles cancellation
_audio_cache = {}  # Pre-generated audio {alert_id: wav_path}
_cache_lock = threading.Lock()


def _start_announcing():
    global _announce_stop
    _announce_stop = True
    import subprocess
    subprocess.run(["killall", "aplay"], capture_output=True)
    import time
    time.sleep(0.3)
    _announce_stop = False
    return True

def _stop_announcing():
    pass  # No lock to release

def precache_audio(alerts):
    """Pre-generate gTTS audio for all alerts in background."""
    global _audio_cache
    import subprocess
    try:
        from gtts import gTTS
    except:
        return
    for alert in alerts:
        aid = alert.get("id", "")
        if aid in _audio_cache:
            continue
        title = alert.get("title", "")
        body = alert.get("body", "")
        desc = alert.get("description", {})
        status = desc.get("status", "")
        t_single = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
        _, t_body_s, t_status_s = translate_alert_text(title, body, status, TTS_LANG)
        text = title + ". " + t_body_s + ". " + t_status_s
        try:
            mp3 = f"/tmp/cache_{hash(aid) & 0xFFFFFFFF}.mp3"
            wav = f"/tmp/cache_{hash(aid) & 0xFFFFFFFF}.wav"
            tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
            tts.save(mp3)
            subprocess.run(["ffmpeg", "-y", "-i", mp3, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav], capture_output=True, timeout=30)
            with _cache_lock:
                _audio_cache[aid] = wav
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cached audio: {title[:30]}")
        except Exception as e:
            print(f"Audio cache error: {e}")


# ==================== API ====================
def save_session():
    try:
        with open(CREDS_FILE, "w") as f:
            json.dump({"username": USERNAME, "password": PASSWORD}, f)
    except: pass

def load_admin_config():
    global USERNAME, PASSWORD, LOGIN_TYPE, TTS_LANG
    try:
        if os.path.exists(ADMIN_CONFIG):
            with open(ADMIN_CONFIG) as f:
                d = json.load(f)
                if d.get("api_username") and d.get("api_password"):
                    USERNAME = d["api_username"]
                    PASSWORD = d["api_password"]
                    LOGIN_TYPE = d.get("login_type", "DEFAULT")
                    TTS_LANG = d.get("tts_lang", "en")
                    return True
    except: pass
    return False

def save_admin_config(api_user, api_pass, login_type="DEFAULT", tts_lang="en"):
    try:
        with open(ADMIN_CONFIG, "w") as f:
            json.dump({"api_username": api_user, "api_password": api_pass, "login_type": login_type, "tts_lang": tts_lang}, f)
        return True
    except: return False

def load_session():
    global USERNAME, PASSWORD, LOGGED_IN
    try:
        if os.path.exists(CREDS_FILE):
            with open(CREDS_FILE) as f:
                d = json.load(f)
                USERNAME = d.get("username", "")
                PASSWORD = d.get("password", "")
                if USERNAME and PASSWORD:
                    LOGGED_IN = True
                    return True
    except: pass
    return False

def get_token():
    global token, token_time
    try:
        resp = requests.get(AUTH_URL, headers={
            "accept": "application/json",
            "username": USERNAME,
            "password": PASSWORD,
            "LoginType": LOGIN_TYPE
        }, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            t = data.get("token") or data.get("data", {}).get("token", "")
            if t:
                token = t.replace("Bearer ", "")
                token_time = time.time()
                print(f"[{now()}] Token refreshed")
                return True
        print(f"[{now()}] Token failed: {resp.status_code}")
        return False
    except Exception as e:
        print(f"[{now()}] Token error: {e}")
        return False


def fetch_alerts():
    global alerts_data, token, token_time
    with fetch_lock:
        # Refresh token if needed
        if not token or (time.time() - token_time) > TOKEN_REFRESH:
            if not get_token():
                return None

        for attempt in range(2):
            try:
                today = datetime.now().strftime("%d/%m/%Y")
                resp = requests.get(
                    f"{ALERTS_URL}?date={today}&type=daily",
                    headers={
                        "accept": "application/json",
                        "authorization": f"Bearer {token}"
                    },
                    timeout=15
                )
                if resp.status_code == 200:
                    alerts_data = resp.json()
                    print(f"[{now()}] Alerts fetched: {alerts_data.get('generalAlerts', {}).get('meta', {}).get('total', 0)} total")
                    return alerts_data
                elif resp.status_code in (401, 403, 422):
                    # Token expired (4hr expiry) — refresh and retry
                    print(f"[{now()}] Token expired (HTTP {resp.status_code}), refreshing... (attempt {attempt+1})")
                    token = ""
                    token_time = 0
                    if get_token():
                        continue  # retry with new token
                    else:
                        break
                else:
                    print(f"[{now()}] Alerts failed: {resp.status_code}")
                    break
            except Exception as e:
                print(f"[{now()}] Alerts error: {e}")
                break
    return None


def now():
    return datetime.now().strftime("%H:%M:%S")


def mark_alerts_as_read(alerts_list):
    """Mark a list of alerts as read via the API."""
    global token, token_time
    if not alerts_list or not token:
        return

    unread = [a for a in alerts_list if not a.get("isRead", True)]
    if not unread:
        return

    notifications = []
    for a in unread:
        notifications.append({
            "id": a.get("id", ""),
            "date": a.get("date_key", a.get("date", "")),
            "type": a.get("type", "")
        })

    if not notifications:
        return

    try:
        resp = requests.patch(
            MARK_READ_URL,
            headers={
                "accept": "application/json",
                "authorization": f"Bearer {token}",
                "content-type": "application/json"
            },
            json={"notifications": notifications},
            timeout=10
        )
        if resp.status_code in (200, 201, 204):
            print(f"[{now()}] Marked {len(notifications)} alerts as read")
            # Update local state
            for a in unread:
                a["isRead"] = True
        elif resp.status_code in (401, 403):
            print(f"[{now()}] Token expired during mark-read, will refresh next cycle")
            token = ""
            token_time = 0
        else:
            print(f"[{now()}] Mark-read failed: {resp.status_code}")
    except Exception as e:
        print(f"[{now()}] Mark-read error: {e}")


def load_announced():
    """Load previously announced alert IDs from file."""
    global announced_ids
    try:
        if os.path.exists(ANNOUNCED_FILE):
            with open(ANNOUNCED_FILE, "r") as f:
                data = json.load(f)
                # Only keep today's IDs
                today = datetime.now().strftime("%Y-%m-%d")
                announced_ids = set(data.get(today, []))
    except Exception:
        announced_ids = set()


def save_announced():
    """Save announced alert IDs to file."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        with open(ANNOUNCED_FILE, "w") as f:
            json.dump({today: list(announced_ids)}, f)
    except Exception:
        pass


def mark_as_announced(alert_id):
    """Mark an alert as announced (for TTS)."""
    announced_ids.add(alert_id)
    save_announced()


def is_announced(alert_id):
    """Check if alert was already announced."""
    return alert_id in announced_ids


def get_unannounced_alerts(alerts_list):
    """Get alerts that haven't been announced yet (for TTS use)."""
    return [a for a in alerts_list if not is_announced(a.get("id", ""))]


def announce_and_mark_read(alert):
    """
    Call this after TTS announces an alert.
    1. Marks alert as announced (won't repeat in TTS)
    2. Marks alert as read via API
    """
    alert_id = alert.get("id", "")
    if alert_id:
        mark_as_announced(alert_id)
        mark_alerts_as_read([alert])
        print(f"[{now()}] Alert announced & marked read: {alert.get('title', '')} ({alert_id})")


# ==================== GTK DISPLAY ====================
COLORS = {
    "high": {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b", "badge": "#dc2626"},
    "medium": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e", "badge": "#d97706"},
    "low": {"bg": "#dbeafe", "border": "#3b82f6", "text": "#1e3a5a", "badge": "#2563eb"},
    "info": {"bg": "#f0fdf4", "border": "#22c55e", "text": "#14532d", "badge": "#16a34a"},
}

CSS = """
window { background-color: #ffffff; }

/* Optimized for 800x480 5-inch display */
.header-bar {
    background: linear-gradient(to right, #1e3a5a, #1e40af);
    padding: 20px 14px;
    border-bottom: 2px solid #3b82f6;
}
.header-title {
    color: white;
    font-size: 20px;
    font-weight: bold;
}
.header-sub {
    color: #93c5fd;
    font-size: 20px;
}

.stats-bar {
    background-color: #f0f4ff;
    padding: 10px 12px;
    border-bottom: 1px solid #e0e4ea;
}
.stat-box {
    background-color: #ffffff;
    border-radius: 7px;
    padding: 8px 10px;
    margin: 2px 4px;
    border: 1px solid #d0d5dd;
}
.stat-num {
    color: #1565c0;
    font-size: 20px;
    font-weight: bold;
}
.stat-label {
    color: #555555;
    font-size: 20px;
}
.stat-num-unread { color: #f87171; }
.stat-num-read { color: #4ade80; }
.stat-num-total { color: #60a5fa; }

.alerts-scroll {
    background-color: #ffffff;
}

.alert-card {
    border-radius: 9px;
    padding: 12px;
    margin: 5px 8px;
    border-left-width: 4px;
    border-left-style: solid;
}
.alert-title {
    font-size: 20px;
    font-weight: bold;
}
.alert-body {
    font-size: 20px;
    margin-top: 2px;
}
.alert-time {
    font-size: 20px;
    color: #64748b;
    margin-top: 2px;
}
.alert-detail {
    font-size: 20px;
    margin-top: 3px;
    padding: 4px 6px;
    border-radius: 4px;
    background-color: rgba(0,0,0,0.05);
}
.alert-badge {
    font-size: 20px;
    font-weight: bold;
    padding: 2px 8px;
    border-radius: 9px;
    color: white;
}
.alert-unread { font-weight: bold; }

.unread-dot {
    color: #ef4444;
    font-size: 20px;
}
.read-check {
    color: #22c55e;
    font-size: 20px;
}

.alert-actions {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid rgba(0,0,0,0.08);
}
.btn-mark-read {
    background: #22c55e;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 20px;
    font-weight: bold;
    padding: 6px 14px;
    min-height: 31px;
}
.btn-mark-read:hover { background: #16a34a; }
.btn-announce {
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 20px;
    font-weight: bold;
    padding: 6px 14px;
    min-height: 31px;
}
.btn-announce:hover { background: #2563eb; }
.btn-done {
    background: #94a3b8;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 20px;
    padding: 4px 12px;
    min-height: 29px;
}
.btn-done:hover { background: #64748b; }

.alert-expander {
    color: #64748b;
    font-size: 20px;
    padding-top: 4px;
}
.alert-expander title {
    color: #64748b;
    font-size: 20px;
}

.offline-card {
    background-color: #fff5f5;
    border-radius: 11px;
    padding: 11px;
    margin: 4px 8px;
    border-left: 4px solid #ef4444;
}
.offline-title {
    color: #c62828;
    font-size: 20px;
    font-weight: bold;
}
.offline-body {
    color: #555555;
    font-size: 20px;
}

.section-header {
    color: #333333;
    font-size: 20px;
    font-weight: bold;
    padding: 8px 12px 4px;
}

.refresh-bar {
    background-color: #1565c0;
    padding: 8px 14px;
    border-top: 1px solid #1255a0;
}
.refresh-text {
    color: #ffffff;
    font-size: 20px;
}

.announce-bar {
    background-color: #1e3a5a;
    padding: 9px 14px;
    border-top: 1px solid #3b82f6;
}
.announce-text {
    color: #60a5fa;
    font-size: 20px;
    font-weight: bold;
    font-family: monospace;
}

.announce-overlay {
    background-color: rgba(0, 0, 0, 0.88);
    border-radius: 20px;
    padding: 33px 24px;
    border: 1px solid rgba(59, 130, 246, 0.3);
}
.announce-overlay-icon {
    color: #60a5fa;
    font-size: 20px;
}
.announce-overlay-text {
    color: #ffffff;
    font-size: 20px;
    font-family: monospace;
    font-weight: bold;
    min-height: 66px;
}
.announce-overlay-title {
    color: #94a3b8;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 1px;
}


.header-lang {
    background: #0d2b5e;
    color: #93c5fd;
    border: 1px solid #1e40af;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 20px;
    min-height: 24px;
}

.refresh-btn {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 15px;
    padding: 2px;
    min-width: 36px;
    min-height: 36px;
}
.refresh-btn:hover {
    background: rgba(255,255,255,0.25);
}
.refresh-btn:active {
    background: rgba(255,255,255,0.35);
}

.header-clock {
    color: white;
    font-size: 20px;
    font-weight: bold;
}
.header-date {
    color: #93c5fd;
    font-size: 20px;
}

.no-alerts {
    color: #2e7d32;
    font-size: 20px;
    font-weight: bold;
    padding: 44px;
}
"""


class LoginWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="AquaBox Login")
        self.set_default_size(800, 480)
        self.fullscreen()
        self.set_app_paintable(True)
        self._kb_visible = False
        self._wave_offset = 0
        self._pulse = 0
        self._drops = []
        self._ripples = []
        self._last_ripple = 0
        for _ in range(30):
            self._drops.append({
                "x": _random.uniform(0, 800), "y": _random.uniform(-50, 480),
                "r": _random.uniform(2, 7), "speed": _random.uniform(1.0, 3.0),
                "alpha": _random.uniform(0.15, 0.45),
                "wobble": _random.uniform(0.5, 2.0), "phase": _random.uniform(0, 6.28)
            })

        # Background drawing
        da = Gtk.DrawingArea()
        da.connect("draw", self._draw_bg)
        overlay = Gtk.Overlay()
        overlay.add(da)

        # Main centered container
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        # Card with rounded feel
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1.0))
        card.set_size_request(420, -1)

        # Logo
        logo_path = "/home/aquabox/Desktop/Aquabox/Fluxgen-Logo.png"
        if os.path.exists(logo_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 320, 100, True)
            logo = Gtk.Image.new_from_pixbuf(pixbuf)
            logo.set_margin_top(20)
            card.pack_start(logo, False, False, 0)

        # Tagline below logo
        tag = Gtk.Label(label="Build a Water-Positive Future")
        tag.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.3, 0.55, 0.8, 0.6))
        tag.modify_font(Pango.FontDescription("Sans italic 8"))
        tag.set_margin_bottom(4)
        card.pack_start(tag, False, False, 2)

        # Divider
        div = Gtk.DrawingArea()
        div.set_size_request(-1, 2)
        div.set_margin_start(30)
        div.set_margin_end(30)
        div.set_margin_top(10)
        div.set_margin_bottom(8)
        div.connect("draw", self._draw_divider)
        card.pack_start(div, False, False, 0)

        # Sign In label
        signin = Gtk.Label(label="Sign In")
        signin.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.05, 0.15, 0.4, 1))
        signin.modify_font(Pango.FontDescription("Sans bold 13"))
        signin.set_halign(Gtk.Align.START)
        signin.set_margin_start(30)
        card.pack_start(signin, False, False, 0)

        # Username
        ulabel = Gtk.Label(label="Username")
        ulabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.25, 0.45, 1))
        ulabel.modify_font(Pango.FontDescription("Sans bold 10"))
        ulabel.set_halign(Gtk.Align.START)
        ulabel.set_margin_start(30)
        ulabel.set_margin_top(8)
        card.pack_start(ulabel, False, False, 0)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Enter your username")
        self.username_entry.modify_font(Pango.FontDescription("Sans 11"))
        self.username_entry.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0))
        self.username_entry.set_margin_start(30)
        self.username_entry.set_margin_end(30)
        card.pack_start(self.username_entry, False, False, 4)

        # Password
        plabel = Gtk.Label(label="Password")
        plabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.25, 0.45, 1))
        plabel.modify_font(Pango.FontDescription("Sans bold 10"))
        plabel.set_halign(Gtk.Align.START)
        plabel.set_margin_start(30)
        plabel.set_margin_top(6)
        card.pack_start(plabel, False, False, 0)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_placeholder_text("Enter your password")
        self.password_entry.set_visibility(False)
        self.password_entry.modify_font(Pango.FontDescription("Sans 11"))
        self.password_entry.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0))
        self.password_entry.set_margin_start(30)
        self.password_entry.set_margin_end(30)
        self.password_entry.connect("activate", self.on_login)
        card.pack_start(self.password_entry, False, False, 4)

        # Error label
        # Check if admin configured credentials
        if not os.path.exists(ADMIN_CONFIG):
            self.error_label = Gtk.Label(label="Admin setup required first")
            self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.5, 0.1, 1))
        else:
            self.error_label = Gtk.Label(label="")
        self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.85, 0.15, 0.15, 1))
        self.error_label.modify_font(Pango.FontDescription("Sans bold 11"))
        card.pack_start(self.error_label, False, False, 2)

        # Login button
        btn = Gtk.Button(label="Login  ➜")
        btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.06, 0.2, 0.6, 0.5))
        btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        btn.modify_font(Pango.FontDescription("Sans bold 13"))
        btn.set_margin_start(30)
        btn.set_margin_end(30)
        btn.set_margin_top(6)
        btn.connect("clicked", self.on_login)
        card.pack_start(btn, False, False, 0)

        # Keyboard button
        kb_btn = Gtk.Button(label="\u2328  Keyboard")
        kb_btn.modify_font(Pango.FontDescription("Sans 11"))
        kb_btn.set_margin_start(30)
        kb_btn.set_margin_end(30)
        kb_btn.set_margin_top(6)
        kb_btn.set_margin_bottom(18)
        kb_btn.connect("clicked", self.toggle_keyboard)
        card.pack_start(kb_btn, False, False, 0)

        admin_btn = Gtk.Button(label="⚙ Admin")
        admin_btn.modify_font(Pango.FontDescription("Sans 8"))
        admin_btn.set_margin_start(30)
        admin_btn.set_margin_end(30)
        admin_btn.set_margin_bottom(10)
        admin_btn.connect("clicked", self._open_admin)
        card.pack_start(admin_btn, False, False, 0)

        outer.pack_start(card, False, False, 0)
        overlay.add_overlay(outer)
        self.add(overlay)
        GLib.timeout_add(40, self._animate)

    def _draw_accent(self, widget, cr):
        w = widget.get_allocated_width()
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgb(0, 0.08, 0.35, 0.8)
        pat.add_color_stop_rgb(0.5, 0.15, 0.55, 0.95)
        pat.add_color_stop_rgb(1, 0.08, 0.35, 0.8)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, 6)
        cr.fill()

    def _draw_divider(self, widget, cr):
        w = widget.get_allocated_width()
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgba(0, 0.8, 0.85, 0.9, 0)
        pat.add_color_stop_rgba(0.3, 0.7, 0.78, 0.88, 0.6)
        pat.add_color_stop_rgba(0.5, 0.4, 0.6, 0.85, 0.8)
        pat.add_color_stop_rgba(0.7, 0.7, 0.78, 0.88, 0.6)
        pat.add_color_stop_rgba(1, 0.8, 0.85, 0.9, 0)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, 2)
        cr.fill()

    def _animate(self):
        self._wave_offset += 0.04
        self._pulse += 0.02
        now_t = time.time()
        for d in self._drops:
            d["y"] -= d["speed"]
            d["x"] += _math.sin(now_t * d["wobble"] + d["phase"]) * 0.5
            if d["y"] < -15:
                d["y"] = _random.uniform(480, 550)
                d["x"] = _random.uniform(0, 800)
        if now_t - self._last_ripple > 0.8:
            self._ripples.append({"x": _random.uniform(50, 750), "y": _random.uniform(340, 440), "r": 0, "max": _random.uniform(30, 60), "alpha": 0.3})
            self._last_ripple = now_t
        self._ripples = [r for r in self._ripples if r["r"] < r["max"]]
        for r in self._ripples:
            r["r"] += 1.2
        self.get_child().get_child().queue_draw()
        return True

    def _draw_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # White background
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()

        t = self._wave_offset

        # Waves at bottom
        for i, (amp, freq, spd, r, g, b_c, alpha) in enumerate([
            (12, 0.018, 1.2, 0.3, 0.65, 0.92, 0.28),
            (8, 0.022, -0.9, 0.4, 0.72, 0.95, 0.2),
            (6, 0.028, 1.5, 0.35, 0.6, 0.88, 0.15),
        ]):
            cr.move_to(0, h)
            base_y = h * 0.76 + i * 14
            for x in range(0, w + 2, 3):
                y = base_y + amp * _math.sin(x * freq + t * spd) + amp * 0.5 * _math.sin(x * freq * 1.7 + t * spd * 0.8 + 1.3)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            pat = cairo.LinearGradient(0, base_y - amp, 0, h)
            pat.add_color_stop_rgba(0, r, g, b_c, alpha * 0.5)
            pat.add_color_stop_rgba(1, r * 0.7, g * 0.8, b_c * 0.9, alpha)
            cr.set_source(pat)
            cr.fill()

        # Water drops
        for d in self._drops:
            s = d["r"]
            cr.save()
            cr.translate(d["x"], d["y"])
            pat = cairo.RadialGradient(0, s * 0.3, 0, 0, 0, s)
            pat.add_color_stop_rgba(0, 0.65, 0.88, 1.0, d["alpha"] * 0.9)
            pat.add_color_stop_rgba(0.5, 0.4, 0.72, 0.95, d["alpha"] * 0.5)
            pat.add_color_stop_rgba(1.0, 0.2, 0.55, 0.88, d["alpha"] * 0.1)
            cr.set_source(pat)
            cr.move_to(0, -s * 1.2)
            cr.curve_to(s * 0.6, -s * 0.3, s * 0.8, s * 0.4, 0, s)
            cr.curve_to(-s * 0.8, s * 0.4, -s * 0.6, -s * 0.3, 0, -s * 1.2)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, d["alpha"] * 0.6)
            cr.arc(-s * 0.15, -s * 0.2, s * 0.2, 0, _math.pi * 2)
            cr.fill()
            cr.restore()

        # Ripples
        for r in self._ripples:
            progress = r["r"] / r["max"]
            alpha = r["alpha"] * (1.0 - progress)
            if alpha > 0.01:
                cr.set_source_rgba(0.4, 0.72, 0.95, alpha)
                cr.set_line_width(1.5 * (1.0 - progress * 0.5))
                cr.arc(r["x"], r["y"], r["r"], 0, _math.pi * 2)
                cr.stroke()

    def _toggle_password(self, button):
        self._pass_visible = not self._pass_visible
        self.password_entry.set_visibility(self._pass_visible)
        button.set_label("○" if self._pass_visible else "●")

    def _open_admin(self, button):
        """Open admin login dialog."""
        dialog = Gtk.Dialog(title="Admin Login", parent=self, flags=0)
        dialog.set_default_size(350, 200)
        dialog.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)

        title = Gtk.Label(label="Admin Login")
        title.modify_font(Pango.FontDescription("Sans bold 14"))
        box.pack_start(title, False, False, 0)

        al = Gtk.Label(label="Admin Username")
        al.modify_font(Pango.FontDescription("Sans bold 10"))
        al.set_halign(Gtk.Align.START)
        box.pack_start(al, False, False, 0)
        admin_user = Gtk.Entry()
        admin_user.set_placeholder_text("Admin username")
        box.pack_start(admin_user, False, False, 0)

        pl = Gtk.Label(label="Admin Password")
        pl.modify_font(Pango.FontDescription("Sans bold 10"))
        pl.set_halign(Gtk.Align.START)
        box.pack_start(pl, False, False, 0)
        admin_pass = Gtk.Entry()
        admin_pass.set_placeholder_text("Admin password")
        admin_pass.set_visibility(False)
        box.pack_start(admin_pass, False, False, 0)

        err = Gtk.Label(label="")
        err.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
        box.pack_start(err, False, False, 0)

        def on_admin_login(btn):
            u = admin_user.get_text().strip()
            p = admin_pass.get_text().strip()
            print("[Admin] Entered: [" + u + "] [" + p + "] Expected: [" + ADMIN_USER + "] [" + ADMIN_PASS + "]")
            if u == ADMIN_USER and p == ADMIN_PASS:
                dialog.destroy()
                self._show_admin_settings()
            else:
                err.set_text("Wrong admin credentials")

        login_btn = Gtk.Button(label="Login")
        login_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.69, 1))
        login_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        login_btn.modify_font(Pango.FontDescription("Sans bold 12"))
        login_btn.connect("clicked", on_admin_login)
        box.pack_start(login_btn, False, False, 5)

        dialog.show_all()

    def _set_api_creds(self, user, passwd, lt):
        global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time, TTS_LANG
        USERNAME = user
        PASSWORD = passwd
        LOGIN_TYPE = lt
        token = ""
        token_time = 0

    def _show_admin_settings(self):
        """Show admin settings page to configure API credentials."""
        dialog = Gtk.Dialog(title="Admin Settings", parent=self, flags=0)
        dialog.set_default_size(400, 350)
        dialog.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)

        title = Gtk.Label(label="API Configuration")
        title.modify_font(Pango.FontDescription("Sans bold 16"))
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.15, 0.35, 1))
        box.pack_start(title, False, False, 0)

        sub = Gtk.Label(label="Configure the username and password for AquaGen API")
        sub.modify_font(Pango.FontDescription("Sans 9"))
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 1))
        box.pack_start(sub, False, False, 4)

        sep = Gtk.Separator()
        box.pack_start(sep, False, False, 6)

        # API Username
        ul = Gtk.Label(label="API Username")
        ul.modify_font(Pango.FontDescription("Sans bold 11"))
        ul.set_halign(Gtk.Align.START)
        box.pack_start(ul, False, False, 0)
        api_user_entry = Gtk.Entry()
        api_user_entry.set_text(USERNAME)
        api_user_entry.modify_font(Pango.FontDescription("Sans 12"))
        box.pack_start(api_user_entry, False, False, 0)

        # API Password
        ppl = Gtk.Label(label="API Password")
        ppl.modify_font(Pango.FontDescription("Sans bold 11"))
        ppl.set_halign(Gtk.Align.START)
        box.pack_start(ppl, False, False, 0)
        api_pass_entry = Gtk.Entry()
        api_pass_entry.set_text(PASSWORD)
        api_pass_entry.modify_font(Pango.FontDescription("Sans 12"))
        box.pack_start(api_pass_entry, False, False, 0)

        # Login Type
        ltl = Gtk.Label(label="Login Type")
        ltl.modify_font(Pango.FontDescription("Sans bold 11"))
        ltl.set_halign(Gtk.Align.START)
        box.pack_start(ltl, False, False, 0)
        lt_combo = Gtk.ComboBoxText()
        lt_combo.append_text("DEFAULT")
        lt_combo.append_text("EXTERNAL")
        lt_combo.set_active(0 if LOGIN_TYPE == "DEFAULT" else 1)
        box.pack_start(lt_combo, False, False, 0)

        # Language selection moved to header bar dropdown

        status = Gtk.Label(label="")
        status.modify_font(Pango.FontDescription("Sans bold 11"))
        box.pack_start(status, False, False, 4)

        def on_save(btn):
            new_user = api_user_entry.get_text().strip()
            new_pass = api_pass_entry.get_text().strip()
            new_lt = lt_combo.get_active_text()

            if not new_user or not new_pass:
                status.set_text("Enter both username and password")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
                return

            self._set_api_creds(new_user, new_pass, new_lt)

            if save_admin_config(new_user, new_pass, new_lt, TTS_LANG):
                save_session()
                status.set_text("Saved! API credentials updated.")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
            else:
                status.set_text("Save failed!")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))

        def on_test(btn):
            old_u, old_p, old_lt = USERNAME, PASSWORD, LOGIN_TYPE
            self._set_api_creds(api_user_entry.get_text().strip(), api_pass_entry.get_text().strip(), lt_combo.get_active_text())

            status.set_text("Testing...")
            status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.3, 0.7, 1))

            def do_test():
                success = get_token()
                def show_result(ok):
                    if ok:
                        status.set_text("Connection successful!")
                        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
                    else:
                        status.set_text("Connection failed! Check credentials.")
                        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
                        pass
                GLib.idle_add(show_result, success)
            threading.Thread(target=do_test, daemon=True).start()

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        test_btn = Gtk.Button(label="Test Connection")
        test_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.5, 0.8, 1))
        test_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        test_btn.modify_font(Pango.FontDescription("Sans bold 11"))
        test_btn.connect("clicked", on_test)
        btn_box.pack_start(test_btn, True, True, 0)

        save_btn = Gtk.Button(label="Save")
        save_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
        save_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        save_btn.modify_font(Pango.FontDescription("Sans bold 11"))
        save_btn.connect("clicked", on_save)
        btn_box.pack_start(save_btn, True, True, 0)

        box.pack_start(btn_box, False, False, 5)

        close_btn = Gtk.Button(label="Close")
        close_btn.modify_font(Pango.FontDescription("Sans 10"))
        close_btn.connect("clicked", lambda b: dialog.destroy())
        box.pack_start(close_btn, False, False, 0)

        dialog.show_all()

    def toggle_keyboard(self, button):
        import subprocess
        if self._kb_visible:
            subprocess.run(["killall", "wvkbd-mobintl"], capture_output=True)
            button.set_label("\u2328  Keyboard")
            self._kb_visible = False
        else:
            env = os.environ.copy()
            env["WAYLAND_DISPLAY"] = "wayland-0"
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            subprocess.Popen(["wvkbd-mobintl", "-L", "300"], env=env)
            button.set_label("\u2328  Hide Keyboard")
            self._kb_visible = True

    def on_login(self, widget):
        global USERNAME, PASSWORD, LOGGED_IN, LOGIN_TYPE
        u = self.username_entry.get_text().strip()
        p = self.password_entry.get_text().strip()
        if not u or not p:
            self.error_label.set_text("Enter username and password")
            return

        # Check if admin has configured API credentials
        if os.path.exists(ADMIN_CONFIG):
            try:
                with open(ADMIN_CONFIG) as f:
                    cfg = json.load(f)
                saved_user = cfg.get("api_username", "")
                saved_pass = cfg.get("api_password", "")
                if saved_user and saved_pass:
                    # User must enter the same credentials admin set
                    if u != saved_user or p != saved_pass:
                        self.error_label.set_text("Invalid credentials")
                        return
            except:
                pass

        USERNAME = u
        PASSWORD = p
        self.error_label.set_text("Logging in...")
        def try_login():
            success = get_token()
            GLib.idle_add(self._login_result, success)
        threading.Thread(target=try_login, daemon=True).start()

    def _login_result(self, success):
        if success:
            global LOGGED_IN, USERNAME, PASSWORD, LOGIN_TYPE
            LOGGED_IN = True
            save_session()
            # Admin config already set by admin page
            # Kill keyboard if open
            import subprocess
            subprocess.run(["killall", "wvkbd-mobintl"], capture_output=True)
            self.destroy()
            win = AlertsWindow()
            win.connect("destroy", lambda w: Gtk.main_quit() if LOGGED_IN else None)
            win.show_all()
        else:
            self.error_label.set_text("Login failed. Check username/password.")
            # credentials handled by _set_api_creds
            pass  # handled by _set_api_creds
            pass

class AlertsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="AquaBox Alerts")
        self.set_default_size(800, 480)
        self.fullscreen()

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main layout with overlay for announcements
        overlay = Gtk.Overlay()
        self.add(overlay)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add(self.main_box)

        # Center overlay for typing animation
        # Overlay container with typing label + close button
        self.overlay_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.overlay_container.set_halign(Gtk.Align.CENTER)
        self.overlay_container.set_valign(Gtk.Align.CENTER)
        self.overlay_container.get_style_context().add_class("announce-overlay")

        # Close button row
        close_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        close_row.override_background_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn = Gtk.Button(label="\u2715")
        close_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 1))
        close_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn.modify_font(Pango.FontDescription("Sans bold 16"))
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b: self._cancel_announce())
        close_row.pack_end(close_btn, False, False, 4)
        self.overlay_container.pack_start(close_row, False, False, 0)

        # Typing text label
        self.overlay_label = Gtk.Label(label="")
        self.overlay_label.set_line_wrap(True)
        self.overlay_label.set_max_width_chars(80)
        self.overlay_label.override_color(
            Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        self.overlay_label.modify_font(Pango.FontDescription("Noto Sans bold 14"))
        self.overlay_label.set_margin_start(30)
        self.overlay_label.set_margin_end(30)
        self.overlay_label.set_margin_top(10)
        self.overlay_label.set_margin_bottom(20)
        self.overlay_container.pack_start(self.overlay_label, False, False, 0)

        overlay.add_overlay(self.overlay_container)
        self.overlay_container.set_no_show_all(True)
        self.overlay_container.set_visible(False)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.get_style_context().add_class("header-bar")

        header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label="AquaBox Alerts")
        title.get_style_context().add_class("header-title")
        title.set_halign(Gtk.Align.START)
        self.header_sub = Gtk.Label(label="Fluxgen Sustainable Technologies")
        self.header_sub.get_style_context().add_class("header-sub")
        self.header_sub.set_halign(Gtk.Align.START)
        header_text.pack_start(title, False, False, 0)
        header_text.pack_start(self.header_sub, False, False, 0)
        header.pack_start(header_text, True, True, 0)

        # Right side: Refresh icon button + Clock + Date
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Refresh icon button (circular)
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_size_request(36, 36)
        refresh_icon = Gtk.Label(label="\u21BB")
        refresh_icon.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.9))
        refresh_icon.modify_font(Pango.FontDescription("Sans 20"))
        self.refresh_btn.add(refresh_icon)
        self.refresh_btn.connect("clicked", self.on_refresh_clicked)
        self.refresh_btn.get_style_context().add_class("refresh-btn")
        right_box.pack_start(self.refresh_btn, False, False, 0)

        # Language dropdown
        self._lang_list = ["en", "te", "kn", "ta", "hi", "ml"]
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append_text("ENG")
        self.lang_combo.append_text("TEL")
        self.lang_combo.append_text("KAN")
        self.lang_combo.append_text("TAM")
        self.lang_combo.append_text("HIN")
        self.lang_combo.append_text("MAL")
        lang_idx = 0
        for i, l in enumerate(self._lang_list):
            if l == TTS_LANG:
                lang_idx = i
                break
        self.lang_combo.set_active(lang_idx)
        self.lang_combo.get_style_context().add_class("header-lang")
        self.lang_combo.set_size_request(-1, -1)
        self.lang_combo.connect("changed", self._on_lang_changed)
        right_box.pack_start(self.lang_combo, False, False, 0)



        # Separator
        sep = Gtk.Label(label="|")
        sep.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.25))
        right_box.pack_start(sep, False, False, 0)

        # Clock + Date stacked
        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.clock_label = Gtk.Label()
        self.clock_label.get_style_context().add_class("header-clock")
        self.clock_label.set_halign(Gtk.Align.END)
        self.date_label = Gtk.Label()
        self.date_label.get_style_context().add_class("header-date")
        self.date_label.set_halign(Gtk.Align.END)
        time_box.pack_start(self.clock_label, False, False, 0)
        time_box.pack_start(self.date_label, False, False, 0)
        right_box.pack_start(time_box, False, False, 0)

        # Separator before logout
        sep2 = Gtk.Label(label="|")
        sep2.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.25))
        right_box.pack_start(sep2, False, False, 0)

        # Logout button (arrow out of box symbol)
        logout_btn = Gtk.Button()
        logout_btn.set_size_request(36, 36)
        logout_icon = Gtk.Label(label="→│")
        logout_icon.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 0.9))
        logout_icon.modify_font(Pango.FontDescription("Sans 14"))
        logout_btn.add(logout_icon)
        logout_btn.connect("clicked", self._on_logout)
        logout_btn.get_style_context().add_class("refresh-btn")
        logout_btn.set_tooltip_text("Logout")
        right_box.pack_start(logout_btn, False, False, 0)

        header.pack_end(right_box, False, False, 0)

        self.main_box.pack_start(header, False, False, 0)

        # Stats bar
        self.stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, homogeneous=True)
        self.stats_box.get_style_context().add_class("stats-bar")

        self.stat_unread = self._make_stat("0", "UNREAD", "stat-num-unread")
        self.stat_read = self._make_stat("0", "READ", "stat-num-read")
        self.stat_total = self._make_stat("0", "TOTAL", "stat-num-total")
        self.stat_offline = self._make_stat("0", "OFFLINE", "stat-num-unread")

        self.stat_unread[0].connect("clicked", lambda b: self._scroll_to_section("unread"))
        self.stat_read[0].connect("clicked", lambda b: self._scroll_to_section("read"))
        self.stat_total[0].connect("clicked", lambda b: self._scroll_to_section("top"))
        self.stat_offline[0].connect("clicked", lambda b: self._scroll_to_section("offline"))
        self.stats_box.pack_start(self.stat_unread[0], True, True, 0)
        self.stats_box.pack_start(self.stat_read[0], True, True, 0)
        self.stats_box.pack_start(self.stat_total[0], True, True, 0)
        self.stats_box.pack_start(self.stat_offline[0], True, True, 0)

        self.main_box.pack_start(self.stats_box, False, False, 0)

        # Scrollable alerts area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.get_style_context().add_class("alerts-scroll")
        self.alerts_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.add(self.alerts_container)
        self.main_box.pack_start(scroll, True, True, 0)

        # Bottom section (fixed at bottom)
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Announce typing bar
        self.announce_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.announce_bar.get_style_context().add_class("announce-bar")
        self.announce_label = Gtk.Label(label="")
        self.announce_label.get_style_context().add_class("announce-text")
        self.announce_label.modify_font(Pango.FontDescription("Noto Sans bold 13"))
        self.announce_label.set_halign(Gtk.Align.START)
        self.announce_bar.pack_start(self.announce_label, True, True, 0)
        self.announce_bar.set_no_show_all(True)
        bottom_box.pack_start(self.announce_bar, False, False, 0)

        # Bottom refresh bar
        refresh_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        refresh_bar.get_style_context().add_class("refresh-bar")
        self.refresh_label = Gtk.Label(label="Loading...")
        self.refresh_label.get_style_context().add_class("refresh-text")
        self.refresh_label.set_halign(Gtk.Align.CENTER)
        refresh_bar.pack_start(self.refresh_label, True, True, 0)
        bottom_box.pack_start(refresh_bar, False, False, 0)

        self.main_box.pack_end(bottom_box, False, False, 0)

        # Typing animation state
        self._typing_text = ""
        self._typing_index = 0
        self._typing_timer = None
        self._hide_timer = None
        self._typing_done = True
        self._typing_speed = 55
        self._batch_announcing = False
        self._last_refresh_time = ""
        self._countdown = REFRESH_INTERVAL

        # Start fetching
        self.update_clock()
        GLib.timeout_add_seconds(1, self.update_clock)
        GLib.timeout_add_seconds(1, self._update_countdown)
        self._all_today_alerts = []
        self._all_offline_alerts = []
        GLib.timeout_add(500, self.first_fetch)
        GLib.timeout_add_seconds(REFRESH_INTERVAL, self.refresh_alerts)
        # Offline announced manually via button only

    def _scroll_to_section(self, section):
        """Scroll alerts list to a specific section."""
        target = None
        if section == "unread" and hasattr(self, '_section_unread'):
            target = self._section_unread
        elif section == "read" and hasattr(self, '_section_read'):
            target = self._section_read
        elif section == "offline" and hasattr(self, '_section_offline'):
            target = self._section_offline
        elif section == "top":
            # Scroll to top
            adj = self.alerts_container.get_parent().get_vadjustment()
            adj.set_value(0)
            return

        if target:
            def do_scroll():
                alloc = target.get_allocation()
                adj = self.alerts_container.get_parent().get_vadjustment()
                adj.set_value(alloc.y)
            GLib.idle_add(do_scroll)

    def _update_counters(self, delta):
        """Instantly update unread/read counters."""
        try:
            cur_unread = int(self.stat_unread[1].get_text())
            cur_read = int(self.stat_read[1].get_text())
            self.stat_unread[1].set_text(str(max(0, cur_unread - delta)))
            self.stat_read[1].set_text(str(cur_read + delta))
        except Exception:
            pass

    def _make_stat(self, num, label, css_class):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("stat-box")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        num_label = Gtk.Label(label=num)
        num_label.get_style_context().add_class("stat-num")
        num_label.get_style_context().add_class(css_class)
        text_label = Gtk.Label(label=label)
        text_label.get_style_context().add_class("stat-label")
        box.pack_start(num_label, False, False, 0)
        box.pack_start(text_label, False, False, 0)
        btn.add(box)
        return (btn, num_label)

    def update_clock(self):
        self.clock_label.set_text(datetime.now().strftime("%I:%M:%S %p"))
        self.date_label.set_text(datetime.now().strftime("%d %b %Y, %A"))
        return True

    def _update_countdown(self):
        """Decrease countdown every second and update refresh bar."""
        if self._countdown > 0:
            self._countdown -= 1
        ts = self._last_refresh_time or "--:--:--"
        self.refresh_label.set_text(
            f"API Refreshed: {ts} | "
            f"Next: {self._countdown}s | "
            f"{datetime.now().strftime('%d %b %Y')}"
        )
        return True

    def _on_logout(self, button):
        global _announce_stop, _auto_announcing
        # If announce is running, stop it first then logout
        if _auto_announcing:
            # Let announce complete, then logout
            def wait_and_logout():
                while _auto_announcing:
                    time.sleep(0.5)
                GLib.idle_add(self._do_logout)
            button.set_sensitive(False)
            threading.Thread(target=wait_and_logout, daemon=True).start()
            return
        self._do_logout()

    def _do_logout(self):
        global USERNAME, PASSWORD, LOGGED_IN
        USERNAME = ""
        PASSWORD = ""
        LOGGED_IN = False
        import subprocess
        subprocess.run(["rm", "-f", CREDS_FILE], capture_output=True)
        subprocess.run(["killall", "wvkbd-mobintl"], capture_output=True)
        subprocess.run(["killall", "aplay"], capture_output=True)
        login = LoginWindow()
        login.connect("destroy", lambda w: None if LOGGED_IN else Gtk.main_quit())
        login.show_all()
        self.hide()
        self.destroy()

    def _on_lang_changed(self, combo):
        global TTS_LANG
        idx = combo.get_active()
        TTS_LANG = self._lang_list[idx]
        # Save to admin config
        try:
            import json
            if os.path.exists(ADMIN_CONFIG):
                with open(ADMIN_CONFIG) as f:
                    cfg = json.load(f)
                cfg["tts_lang"] = TTS_LANG
                with open(ADMIN_CONFIG, "w") as f:
                    json.dump(cfg, f)
        except: pass
        # Clear audio cache for new language
        _audio_cache.clear()

    def on_refresh_clicked(self, button):
        global _announce_stop
        _announce_stop = False
        self.refresh_label.set_text("Refreshing...")
        self._countdown = REFRESH_INTERVAL
        button.set_sensitive(False)
        def do_refresh():
            self._fetch_and_update()
            GLib.idle_add(button.set_sensitive, True)
        threading.Thread(target=do_refresh, daemon=True).start()

    def _quick_retry(self):
        """Quick retry after fetch failure."""
        print(f"[{now()}] Quick retry fetch...")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return False  # Don't repeat

    def first_fetch(self):
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return False

    def refresh_alerts(self):
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return True

    _last_fetch_time_actual = 0

    def _fetch_and_update(self):
        global _refresh_queued
        # If announce is running, queue the refresh
        if _auto_announcing:
            _refresh_queued = True
            print("[" + now() + "] Refresh queued - announce in progress")
            return
        # Prevent fetching more than once every 30 seconds
        now_ts = time.time()
        if now_ts - self._last_fetch_time_actual < 30:
            return
        self._last_fetch_time_actual = now_ts
        data = fetch_alerts()
        # Pre-cache audio for instant playback
        if data:
            today = data.get("generalAlerts", {}).get("alerts", {}).get("today", [])
            if today:
                threading.Thread(target=precache_audio, args=(today,), daemon=True).start()
        GLib.idle_add(self._render_alerts, data)

    def _render_alerts(self, data):
        # Clear old alerts
        for child in self.alerts_container.get_children():
            self.alerts_container.remove(child)

        if not data:
            lbl = Gtk.Label(label="Failed to fetch alerts. Retrying...")
            lbl.get_style_context().add_class("no-alerts")
            lbl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.4, 0.4, 1))
            self.alerts_container.pack_start(lbl, True, True, 20)
            prev = f" | Last success: {self._last_refresh_time}" if self._last_refresh_time else ""
            self.refresh_label.set_text(f"Error | Quick retry in 10s{prev}")
            # Will retry on next scheduled refresh
            self.alerts_container.show_all()
            return

        general = data.get("generalAlerts", {})
        offline = data.get("offlineAlerts", {})
        meta = general.get("meta", {})

        # Update stats
        self.stat_unread[1].set_text(str(meta.get("unread", 0)))
        self.stat_read[1].set_text(str(meta.get("read", 0)))
        self.stat_total[1].set_text(str(meta.get("total", 0)))
        off_count = len(offline.get("alerts", {}).get("today", []))
        self.stat_offline[1].set_text(str(off_count))

        # General alerts - split into Unread and Read sections
        today_alerts = general.get("alerts", {}).get("today", [])
        unread_alerts = [a for a in today_alerts if not a.get("isRead", True)]
        read_alerts = [a for a in today_alerts if a.get("isRead", True)]

        # Store alerts for "Announce All"
        self._all_today_alerts = today_alerts

        if not today_alerts:
            lbl = Gtk.Label(label="No alerts today")
            lbl.get_style_context().add_class("no-alerts")
            self.alerts_container.pack_start(lbl, True, True, 20)
        else:
            # ---- ANNOUNCE ALL BUTTON ----
            btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_row.set_margin_start(10)
            btn_row.set_margin_end(10)
            btn_row.set_margin_top(4)
            btn_row.set_margin_bottom(4)

            announce_all_btn = Gtk.Button(label="\u266A  Announce All Alerts")
            announce_all_btn.get_style_context().add_class("btn-announce")
            announce_all_btn.connect("clicked", self._on_announce_all)
            btn_row.pack_start(announce_all_btn, True, True, 0)

            self.alerts_container.pack_start(btn_row, False, False, 0)

            # ---- UNREAD SECTION ----
            self._section_unread = Gtk.Label(label="")
            self._section_unread.set_size_request(-1, 0)
            self.alerts_container.pack_start(self._section_unread, False, False, 0)
            unread_header = Gtk.Label(label=f"\u25CF  UNREAD ({len(unread_alerts)})")
            unread_header.get_style_context().add_class("section-header")
            unread_header.set_halign(Gtk.Align.START)
            unread_header.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.97, 0.33, 0.33, 1))
            self.alerts_container.pack_start(unread_header, False, False, 0)

            if unread_alerts:
                for alert in unread_alerts:
                    card = self._make_alert_card(alert)
                    self.alerts_container.pack_start(card, False, False, 0)
                # Auto-announce only NEW unread alerts (not already announced)
                new_unread = [a for a in unread_alerts if a.get('id','') not in _announced_ids]
                if new_unread and not _auto_announcing:
                    threading.Thread(target=self._auto_announce_unread, args=(list(new_unread),), daemon=True).start()
            else:
                no_unread = Gtk.Label(label="All caught up! No unread alerts.")
                no_unread.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.26, 0.77, 0.37, 0.8))
                no_unread.modify_font(Pango.FontDescription("Sans 11"))
                no_unread.set_margin_top(6)
                no_unread.set_margin_bottom(6)
                self.alerts_container.pack_start(no_unread, False, False, 0)

            # ---- SEPARATOR ----
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.25, 0.33, 1))
            self.alerts_container.pack_start(sep, False, False, 6)

            # ---- READ SECTION ----
            self._section_read = Gtk.Label(label="")
            self._section_read.set_size_request(-1, 0)
            self.alerts_container.pack_start(self._section_read, False, False, 0)
            read_header = Gtk.Label(label=f"\u25CF  READ ({len(read_alerts)})")
            read_header.get_style_context().add_class("section-header")
            read_header.set_halign(Gtk.Align.START)
            read_header.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.26, 0.77, 0.37, 1))
            self.alerts_container.pack_start(read_header, False, False, 0)

            if read_alerts:
                for alert in read_alerts:
                    card = self._make_alert_card(alert)
                    self.alerts_container.pack_start(card, False, False, 0)
            else:
                no_read = Gtk.Label(label="No read alerts yet.")
                no_read.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.58, 0.64, 0.72, 0.7))
                no_read.modify_font(Pango.FontDescription("Sans 11"))
                no_read.set_margin_top(6)
                no_read.set_margin_bottom(6)
                self.alerts_container.pack_start(no_read, False, False, 0)

        # Offline alerts
        offline_list = offline.get("alerts", {}).get("today", [])
        self._all_offline_alerts = offline_list
        self._section_offline = Gtk.Label(label="")
        self._section_offline.set_size_request(-1, 0)
        self.alerts_container.pack_start(self._section_offline, False, False, 0)
        if offline_list:
            # Announce Offline button
            off_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            off_btn_row.set_margin_start(10)
            off_btn_row.set_margin_end(10)
            off_btn_row.set_margin_top(4)
            off_btn_row.set_margin_bottom(4)

            announce_off_btn = Gtk.Button(label="♪  Announce Offline Units")
            announce_off_btn.get_style_context().add_class("btn-announce")
            announce_off_btn.modify_font(Pango.FontDescription("Sans bold 16"))
            announce_off_btn.connect("clicked", self._on_announce_offline)
            off_btn_row.pack_start(announce_off_btn, True, True, 0)
            self.alerts_container.pack_start(off_btn_row, False, False, 0)

            sec_label = Gtk.Label(label=f"OFFLINE UNITS ({len(offline_list)})")
            sec_label.get_style_context().add_class("section-header")
            sec_label.set_halign(Gtk.Align.START)
            self.alerts_container.pack_start(sec_label, False, False, 4)

            for alert in offline_list:
                card = self._make_offline_card(alert)
                self.alerts_container.pack_start(card, False, False, 0)

        self._last_refresh_time = datetime.now().strftime('%I:%M:%S %p')
        self._countdown = REFRESH_INTERVAL
        self.alerts_container.show_all()

    def _make_alert_card(self, alert):
        importance = alert.get("importanceLevel", "info")
        colors = COLORS.get(importance, COLORS["info"])
        is_unread = not alert.get("isRead", True)

        is_announced_alert = False  # Always allow re-announce

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("alert-card")

        bg_rgba = self._hex_to_rgba(colors["bg"])
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*bg_rgba))

        # Top row: status dot + title + badge + time
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Unread/Read indicator
        if is_unread:
            dot = Gtk.Label(label="\u25CF")  # Filled circle
            dot.get_style_context().add_class("unread-dot")
            dot.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.94, 0.27, 0.27, 1))
            dot.set_tooltip_text("Unread - will be marked read after announcement")
        else:
            dot = Gtk.Label(label="\u25CF")  # Green filled circle
            dot.get_style_context().add_class("read-check")
            dot.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.13, 0.77, 0.37, 1))
            dot.set_tooltip_text("Read" + (" & Announced" if is_announced_alert else ""))
        top.pack_start(dot, False, False, 0)

        title = Gtk.Label(label=alert.get("title", "Unknown"))
        title.get_style_context().add_class("alert-title")
        if is_unread:
            title.get_style_context().add_class("alert-unread")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*self._hex_to_rgba(colors["text"])))
        title.set_halign(Gtk.Align.START)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_max_width_chars(28)
        top.pack_start(title, True, True, 0)

        # Badge
        badge = Gtk.Label(label=importance.upper())
        badge.get_style_context().add_class("alert-badge")
        badge.override_background_color(
            Gtk.StateFlags.NORMAL,
            Gdk.RGBA(*self._hex_to_rgba(colors["badge"]))
        )
        top.pack_end(badge, False, False, 0)

        # Time
        time_str = alert.get("time", "")
        time_label = Gtk.Label(label=time_str)
        time_label.get_style_context().add_class("alert-time")
        top.pack_end(time_label, False, False, 4)

        card.pack_start(top, False, False, 0)

        # Body
        body_text = alert.get("body", "")
        if body_text:
            body = Gtk.Label(label=body_text)
            body.get_style_context().add_class("alert-body")
            body.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*self._hex_to_rgba(colors["text"])))
            body.set_halign(Gtk.Align.START)
            body.set_line_wrap(True)
            card.pack_start(body, False, False, 0)

        # Details
        desc = alert.get("description", {})
        details = desc.get("details", [])
        if details:
            detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            detail_box.get_style_context().add_class("alert-detail")
            for d in details[:3]:
                dl = Gtk.Label(label=f"  {d}")
                dl.get_style_context().add_class("alert-detail")
                dl.set_halign(Gtk.Align.START)
                dl.set_line_wrap(True)
                dl.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(*self._hex_to_rgba(colors["text"])))
                detail_box.pack_start(dl, False, False, 0)
            card.pack_start(detail_box, False, False, 0)

        # Action buttons - always visible
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.get_style_context().add_class("alert-actions")

        if is_unread:
            read_btn = Gtk.Button(label="\u25CF  Mark Read")
            read_btn.get_style_context().add_class("btn-mark-read")
            read_btn.connect("clicked", self._on_mark_read, alert)
            actions.pack_start(read_btn, False, False, 0)

        announce_btn = Gtk.Button(label="\u266A  Announce")
        announce_btn.get_style_context().add_class("btn-announce")
        announce_btn.connect("clicked", self._on_announce, alert)
        actions.pack_start(announce_btn, False, False, 0)

        card.pack_start(actions, False, False, 0)

        return card

    def _auto_announce_unread(self, alerts):
        """Auto-announce unread alerts one by one."""
        global _auto_announcing, _announced_ids
        if _auto_announcing:
            return
        _auto_announcing = True
        import subprocess
        _start_announcing()
        time.sleep(3)

        for i, alert in enumerate(alerts):
            if _announce_stop:
                break
            title = alert.get("title", "")
            body = alert.get("body", "")
            desc = alert.get("description", {})
            status = desc.get("status", "")
            text = "Unread alert " + str(i+1) + " of " + str(len(alerts)) + ". " + title + ". " + body + ". " + status

            try:
                aid = alert.get("id", "")
                wav_path = _audio_cache.get(aid)
                if not wav_path or not os.path.exists(str(wav_path)):
                    from gtts import gTTS
                    mp3_path = "/tmp/auto_unread_" + str(i) + ".mp3"
                    wav_path = "/tmp/auto_unread_" + str(i) + ".wav"
                    if _announce_stop: break
                    tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)

                audio_dur = 0
                try:
                    audio_dur = os.path.getsize(wav_path) / (44100 * 2)
                except:
                    audio_dur = 5
                GLib.idle_add(self._start_typing, text, audio_dur)
                subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                # Wait for typing to finish
                for _ in range(200):
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.02)
                time.sleep(0.5)
            except Exception as e:
                print("[" + now() + "] Auto-announce unread error: " + str(e))

            _announced_ids.add(alert.get("id", ""))
            announce_and_mark_read(alert)
            GLib.idle_add(self._update_counters, 1)
            time.sleep(0.5)

        _auto_announcing = False
        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")
        # Process queued refresh
        global _refresh_queued
        if _refresh_queued:
            _refresh_queued = False
            print("[" + now() + "] Processing queued refresh")
            time.sleep(1)
            GLib.idle_add(self.refresh_alerts)
        _stop_announcing()

    def _auto_announce_offline_timer(self):
        """Auto-announce offline alerts every 1 hour."""
        if not self._all_offline_alerts:
            return True
        print("[" + now() + "] Auto-announcing " + str(len(self._all_offline_alerts)) + " offline alerts (hourly)")

        def do_offline_auto():
            import subprocess
            _start_announcing()
            alerts = list(self._all_offline_alerts)

            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = "Offline unit " + str(i+1) + " of " + str(len(alerts)) + ". " + title + ". " + status

                try:
                    from gtts import gTTS
                    mp3_path = "/tmp/auto_offline_" + str(i) + ".mp3"
                    wav_path = "/tmp/auto_offline_" + str(i) + ".wav"
                    if _announce_stop: break
                    tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                    time.sleep(1)
                except Exception as e:
                    print("[" + now() + "] Auto offline announce error: " + str(e))
                time.sleep(0.5)

        threading.Thread(target=do_offline_auto, daemon=True).start()
        return True  # Keep timer  # Keep timer running

    def _on_announce_offline(self, button):
        """Announce all offline units."""
        alerts = self._all_offline_alerts
        if not alerts:
            return
        button.set_sensitive(False)
        button.set_label(f"Announcing {len(alerts)} offline units...")

        def do_offline():
            import subprocess
            _start_announcing()
            self._batch_announcing = True
            total = len(alerts)

            # Pre-generate all audio
            GLib.idle_add(button.set_label, "Generating audio...")
            audio_files = []
            texts = []
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
                _, _, t_status = translate_alert_text(title, "", status, TTS_LANG)
                text = t["offline_unit"] + " " + str(i+1) + " " + t["of"] + " " + str(total) + ". " + title + ". " + t_status
                texts.append(text)
                try:
                    from gtts import gTTS
                    mp3_path = "/tmp/offline_" + str(i) + ".mp3"
                    wav_path = "/tmp/offline_" + str(i) + ".wav"
                    if _announce_stop: pass  # cancelled
                    tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)
                    audio_files.append(wav_path)
                except Exception as e:
                    audio_files.append(None)

            # Play each with animation
            GLib.idle_add(button.set_label, "Playing offline alerts...")
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                if i >= len(audio_files) or not audio_files[i]:
                    continue

                audio_duration = 0
                try:
                    audio_duration = os.path.getsize(audio_files[i]) / (44100 * 2)
                except:
                    audio_duration = 5

                self._typing_done = False
                GLib.idle_add(self._start_typing, texts[i], audio_duration)
                time.sleep(0.3)

                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:0,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while audio_proc.poll() is None:
                    if _announce_stop:
                        audio_proc.kill()
                        break
                    time.sleep(0.1)

                for _ in range(100):
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.01)

                time.sleep(0.5)

            self._batch_announcing = False
            _stop_announcing()
            if _refresh_queued:
                _refresh_queued = False
                time.sleep(1)
                GLib.idle_add(self.refresh_alerts)
            GLib.idle_add(self._after_announce_offline, button)

        threading.Thread(target=do_offline, daemon=True).start()

    def _after_announce_offline(self, button):
        button.set_label("♪  Announce Offline Units")
        button.set_sensitive(True)

    def _on_announce_all(self, button):
        """Announce all alerts one by one."""
        alerts = self._all_today_alerts
        if not alerts:
            return
        button.set_sensitive(False)
        button.set_label(f"Announcing {len(alerts)} alerts...")

        def do_all():
            import subprocess
            _start_announcing()
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    print(f"[{now()}] Announce all cancelled at alert {i+1}")
                    break
                title = alert.get("title", "")
                body = alert.get("body", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)
                text = t["alert"] + ". " + title + ". " + t_body + ". " + t_status

                # Generate audio first
                try:
                    aid = alert.get("id", "")
                    wav_path = _audio_cache.get(aid)
                    if not wav_path or not os.path.exists(wav_path):
                        from gtts import gTTS
                        mp3_path = "/tmp/aquabox_announce_all.mp3"
                        wav_path = "/tmp/aquabox_announce_all.wav"
                        if _announce_stop: break
                        tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
                        tts.save(mp3_path)
                        subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=30)
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                    # Wait for typing animation to catch up with audio
                    time.sleep(1)
                except Exception as e:
                    print(f"[{now()}] Announce all TTS error: {e}")

                announce_and_mark_read(alert)
                time.sleep(0.5)

            self._batch_announcing = False
            _stop_announcing()
            # Process queued refresh
            if _refresh_queued:
                _refresh_queued = False
                time.sleep(1)
                GLib.idle_add(self.refresh_alerts)
            GLib.idle_add(self._after_announce_all, button)

        threading.Thread(target=do_all, daemon=True).start()

    def _after_announce_all(self, button):
        """Update UI after announcing all."""
        button.set_label("\u2713  All Announced")
        button.get_style_context().remove_class("btn-announce")
        button.get_style_context().add_class("btn-done")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _on_mark_read(self, button, alert):
        """Mark single alert as read."""
        button.set_sensitive(False)
        button.set_label("Marking...")
        def do_mark():
            mark_alerts_as_read([alert])
            GLib.idle_add(self._after_mark_read, button)
        threading.Thread(target=do_mark, daemon=True).start()

    def _after_mark_read(self, button):
        """Update UI after marking read."""
        button.set_label("\u25CF  Done")
        button.get_style_context().remove_class("btn-mark-read")
        button.get_style_context().add_class("btn-done")
        # Refresh to move alert to Read section
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _on_announce(self, button, alert):
        """Announce alert via TTS with typing animation."""
        button.set_sensitive(False)
        button.set_label("Speaking...")

        title = alert.get("title", "")
        body = alert.get("body", "")
        desc = alert.get("description", {})
        status = desc.get("status", "")
        t_single = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])
        _, t_body_s, t_status_s = translate_alert_text(title, body, status, TTS_LANG)
        text = title + ". " + t_body_s + ". " + t_status_s

        def do_announce():
            _start_announcing()
            try:
                import subprocess
                aid = alert.get("id", "")
                wav_path = _audio_cache.get(aid)
                if not wav_path or not os.path.exists(wav_path):
                    from gtts import gTTS
                    mp3_path = "/tmp/aquabox_announce.mp3"
                    wav_path = "/tmp/aquabox_announce.wav"
                    if _announce_stop: pass  # cancelled
                    tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=30)
                audio_dur = 0
                try:
                    audio_dur = os.path.getsize(wav_path) / (44100 * 2)
                except:
                    audio_dur = 5
                GLib.idle_add(self._start_typing, text, audio_dur)
                subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
            except Exception as e:
                print(f"[{now()}] Announce TTS error: {e}")

            if not _announce_stop:
                announce_and_mark_read(alert)
            _stop_announcing()
            GLib.idle_add(self._after_announce, button)
        threading.Thread(target=do_announce, daemon=True).start()

    def _start_typing(self, text, duration=0):
        """Start typing animation. duration=estimated audio seconds."""
        self._typing_done = False
        # Cancel any pending hide timer from previous alert
        if self._hide_timer:
            try:
                GLib.source_remove(self._hide_timer)
            except Exception:
                pass
            self._hide_timer = None
        # Cancel any running typing timer
        if self._typing_timer:
            try:
                GLib.source_remove(self._typing_timer)
            except Exception:
                pass
            self._typing_timer = None
        self._typing_text = "\U0001F50A ANNOUNCING: " + text
        self._typing_index = 0
        # Calculate speed: text must finish in 'duration' seconds
        # If no duration given, use 60 WPM default
        total_chars = len(self._typing_text)
        if duration > 0 and total_chars > 0:
            self._typing_speed = max(10, int((duration * 1000 * 0.85) / total_chars))
        else:
            self._typing_speed = 55  # default
        self.overlay_label.set_text("")
        self.overlay_container.set_no_show_all(False)
        self.overlay_container.show_all()
        self.overlay_container.set_visible(True)
        self.announce_label.set_text("")
        self.announce_bar.show()
        self.announce_label.show()
        self.announce_bar.set_visible(True)

        print(f"[{now()}] Typing started: {text[:50]}...")
        self._typing_timer = GLib.timeout_add(self._typing_speed, self._typing_tick)

    def _typing_tick(self):
        """Type one character per tick."""
        if self._typing_index <= len(self._typing_text):
            shown = self._typing_text[:self._typing_index] + "\u2588"
            self.overlay_label.set_text(shown)
            self.announce_label.set_text(shown)
            self._typing_index += 1
            return True
        else:
            done = self._typing_text + "  \u2713"
            self.overlay_label.set_text(done)
            self.announce_label.set_text(done)
            self._typing_timer = None
            print(f"[{now()}] Typing complete")
            if not self._batch_announcing:
                self._hide_timer = GLib.timeout_add(5000, self._hide_announce_overlay)
            return False

    def _cancel_announce(self):
        """Cancel ongoing announcement."""
        global _announce_stop, _auto_announcing
        _announce_stop = True
        _auto_announcing = False
        self._typing_done = True
        self._batch_announcing = False
        import subprocess
        subprocess.run(["killall", "aplay"], capture_output=True)
        self._hide_announce_overlay()
        # Reset all announce buttons immediately
        GLib.idle_add(self._reset_announce_buttons)
        print(f"[{now()}] Announcement cancelled")

    def _reset_announce_buttons(self):
        """Reset all announce buttons to clickable state."""
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _hide_announce_overlay(self):
        """Hide overlay and bottom bar."""
        self.overlay_container.set_visible(False)
        self.overlay_container.set_no_show_all(True)
        self.overlay_container.hide()
        self.announce_bar.hide()
        self.announce_bar.set_visible(False)
        self._typing_timer = None
        return False

    def _after_announce(self, button):
        """Update UI after announcement."""
        button.set_label("\u25CF  Announced")
        button.get_style_context().remove_class("btn-announce")
        button.get_style_context().add_class("btn-done")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _make_offline_card(self, alert):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.get_style_context().add_class("offline-card")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label=alert.get("title", "Unknown"))
        title.get_style_context().add_class("offline-title")
        title.set_halign(Gtk.Align.START)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        top.pack_start(title, True, True, 0)

        time_label = Gtk.Label(label=alert.get("time", ""))
        time_label.get_style_context().add_class("alert-time")
        top.pack_end(time_label, False, False, 0)
        card.pack_start(top, False, False, 0)

        body = Gtk.Label(label=alert.get("body", ""))
        body.get_style_context().add_class("offline-body")
        body.set_halign(Gtk.Align.START)
        body.set_line_wrap(True)
        card.pack_start(body, False, False, 0)

        return card

    def _hex_to_rgba(self, hex_color):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255
        return (r, g, b, 1.0)


# ==================== MAIN ====================
def main():
    signal.signal(signal.SIGINT, lambda s, f: Gtk.main_quit())
    signal.signal(signal.SIGTERM, lambda s, f: Gtk.main_quit())

    os.environ["WAYLAND_DISPLAY"] = "wayland-0"
    os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
    os.environ["GDK_BACKEND"] = "wayland"

    load_announced()

    print("=" * 50)
    print("  AquaBox Alerts Display")
    print(f"  Refresh: every {REFRESH_INTERVAL}s")
    print(f"  Announced alerts tracked: {len(announced_ids)}")
    print("=" * 50)

    load_admin_config()
    load_session()

    if LOGGED_IN:
        # Saved session - go directly to alerts
        win = AlertsWindow()
        win.connect("destroy", lambda w: Gtk.main_quit() if LOGGED_IN else None)
        win.show_all()
    else:
        # Show login screen
        login = LoginWindow()
        login.connect("destroy", lambda w: None if LOGGED_IN else Gtk.main_quit())
        login.show_all()

    Gtk.main()


if __name__ == "__main__":
    main()
