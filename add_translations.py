import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add translation dictionary after TTS_LANG
TRANSLATIONS = '''
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

'''

content = content.replace(
    'TTS_LANG = "en"  # en=English, te=Telugu, hi=Hindi, kn=Kannada, ta=Tamil',
    'TTS_LANG = "en"  # en=English, te=Telugu, hi=Hindi, kn=Kannada, ta=Tamil\n' + TRANSLATIONS
)

# 2. Update all announce text builders to use translate_alert_text

# Auto-announce unread
content = content.replace(
    '                text = "Unread alert " + str(i+1) + " of " + str(len(alerts)) + ". " + title + ". " + body + ". " + status',
    '                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
    '                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)\n'
    '                text = t["unread_alert"] + " " + str(i+1) + " " + t["of"] + " " + str(len(alerts)) + ". " + title + ". " + t_body + ". " + t_status'
)

# Announce all
content = content.replace(
    '                text = "Alert " + str(i+1) + " of " + str(total) + ". " + title + ". " + body + ". " + status',
    '                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
    '                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)\n'
    '                text = t["alert"] + " " + str(i+1) + " " + t["of"] + " " + str(total) + ". " + title + ". " + t_body + ". " + t_status'
)

# Offline announce
content = content.replace(
    '                text = "Offline unit " + str(i+1) + " of " + str(total) + ". " + title + ". " + status',
    '                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
    '                _, _, t_status = translate_alert_text(title, "", status, TTS_LANG)\n'
    '                text = t["offline_unit"] + " " + str(i+1) + " " + t["of"] + " " + str(total) + ". " + title + ". " + t_status'
)

# Single announce (_on_announce)
content = content.replace(
    '        text = f"Alert {i+1} of {len(alerts)}. {title}. {body}. {status}"',
    '        t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
    '        _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)\n'
    '        text = t["alert"] + ". " + title + ". " + t_body + ". " + t_status'
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Verify
check = 'import py_compile\ntry:\n    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)\n    print("SYNTAX OK")\nexcept py_compile.PyCompileError as e:\n    print("ERROR:", str(e))\n'
sftp2 = ssh.open_sftp()
with sftp2.file('/tmp/check.py', 'w') as f:
    f.write(check)
sftp2.close()
stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
print(stdout.read().decode('utf-8', errors='replace').strip())

ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
ssh.exec_command('killall aplay 2>/dev/null')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
