import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add Hindi and Malayalam to language list button
content = content.replace(
    '        self._lang_list = ["en", "te", "kn", "ta"]',
    '        self._lang_list = ["en", "te", "kn", "ta", "hi", "ml"]'
)
content = content.replace(
    '        self._lang_labels = ["ENG", "TEL", "KAN", "TAM"]',
    '        self._lang_labels = ["ENG", "TEL", "KAN", "TAM", "HIN", "MAL"]'
)

# 2. Add Malayalam translations to TRANSLATIONS dict
# Find the closing of Tamil dict and add Malayalam after it
content = content.replace(
    '    "ta": {\n'
    '        "alert": "எச்சரிக்கை",',
    '    "ml": {\n'
    '        "alert": "മുന്നറിയിപ്പ്",\n'
    '        "of": "ൽ",\n'
    '        "unread_alert": "വായിക്കാത്ത മുന്നറിയിപ്പ്",\n'
    '        "offline_unit": "ഓഫ്‌ലൈൻ യൂണിറ്റ്",\n'
    '        "filled": "നിറഞ്ഞു",\n'
    '        "stock_upper": "ജല നിരപ്പ് ഉയർന്ന പരിധി എത്തി",\n'
    '        "stock_lower": "ജല നിരപ്പ് താഴ്ന്ന പരിധി എത്തി",\n'
    '        "daily_limit": "ദൈനംദിന പരിധി എത്തി",\n'
    '        "daily_limit_90": "ദൈനംദിന പരിധിയുടെ 90 ശതമാനം എത്തി",\n'
    '        "abnormal": "അസാധാരണ ജല ഉപയോഗം കണ്ടെത്തി",\n'
    '        "offline": "ഉപകരണം ഓഫ്‌ലൈനിലാണ്",\n'
    '        "online": "ഉപകരണം വീണ്ടും ഓൺലൈനിലാണ്",\n'
    '        "at": "സമയം",\n'
    '        "current_stock": "നിലവിലെ സ്റ്റോക്ക്",\n'
    '        "upper_limit": "ഉയർന്ന പരിധി",\n'
    '        "lower_limit": "താഴ്ന്ന പരിധി",\n'
    '    },\n'
    '    "ta": {\n'
    '        "alert": "எச்சரிக்கை",'
)

# 3. Add admin language dropdown options for Hindi and Malayalam
content = content.replace(
    '        lang_combo.append_text("Tamil")\n'
    '        lang_map = {"en": 0, "te": 1, "hi": 2, "kn": 3, "ta": 4}',
    '        lang_combo.append_text("Tamil")\n'
    '        lang_combo.append_text("Malayalam")\n'
    '        lang_map = {"en": 0, "te": 1, "hi": 2, "kn": 3, "ta": 4, "ml": 5}'
)
content = content.replace(
    '            lang_options = ["en", "te", "hi", "kn", "ta"]',
    '            lang_options = ["en", "te", "hi", "kn", "ta", "ml"]'
)

# 4. Fix ALL announce text builders to use translate_alert_text
# Find the auto-announce-unread text builder
content = content.replace(
    '                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
    '                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)\n'
    '                text = t["unread_alert"] + " " + str(i+1) + " " + t["of"] + " " + str(len(alerts)) + ". " + title + ". " + t_body + ". " + t_status',
    '                t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
    '                _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)\n'
    '                text = t.get("unread_alert", "Unread alert") + " " + str(i+1) + " " + t.get("of", "of") + " " + str(len(alerts)) + ". " + title + ". " + t_body + ". " + t_status'
)

# 5. Fix single announce - find the one that builds text for _on_announce
# The single announce text builder
old_single_text = '        text = f"Alert {i+1} of {len(alerts)}. {title}. {body}. {status}"'
if old_single_text in content:
    content = content.replace(
        old_single_text,
        '        t = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
        '        _, t_body, t_status = translate_alert_text(title, body, status, TTS_LANG)\n'
        '        text = t.get("alert", "Alert") + ". " + title + ". " + t_body + ". " + t_status'
    )

# Check for any remaining English-only text builders
# The _on_announce single alert text
old_single2 = '        text = f"{title}. {body}. {status}"'
if old_single2 in content:
    content = content.replace(
        old_single2,
        '        t_single = TRANSLATIONS.get(TTS_LANG, TRANSLATIONS["en"])\n'
        '        _, t_body_s, t_status_s = translate_alert_text(title, body, status, TTS_LANG)\n'
        '        text = title + ". " + t_body_s + ". " + t_status_s'
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
result = stdout.read().decode('utf-8', errors='replace').strip()
print(result)

if 'SYNTAX OK' in result:
    ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
    ssh.exec_command('killall aplay 2>/dev/null')
    time.sleep(2)
    ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
    print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
