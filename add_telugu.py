import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add TTS_LANG config variable
content = content.replace(
    'LOGIN_TYPE = "DEFAULT"',
    'LOGIN_TYPE = "DEFAULT"\nTTS_LANG = "en"  # en=English, te=Telugu, hi=Hindi, kn=Kannada, ta=Tamil'
)

# 2. Save/load TTS_LANG in admin config
content = content.replace(
    'def save_admin_config(api_user, api_pass, login_type="DEFAULT"):',
    'def save_admin_config(api_user, api_pass, login_type="DEFAULT", tts_lang="en"):'
)

content = content.replace(
    '        json.dump({"api_username": api_user, "api_password": api_pass, "login_type": login_type}, f)',
    '        json.dump({"api_username": api_user, "api_password": api_pass, "login_type": login_type, "tts_lang": tts_lang}, f)'
)

content = content.replace(
    'def load_admin_config():\n    global USERNAME, PASSWORD, LOGIN_TYPE',
    'def load_admin_config():\n    global USERNAME, PASSWORD, LOGIN_TYPE, TTS_LANG'
)

content = content.replace(
    '                    LOGIN_TYPE = d.get("login_type", "DEFAULT")\n                    return True',
    '                    LOGIN_TYPE = d.get("login_type", "DEFAULT")\n                    TTS_LANG = d.get("tts_lang", "en")\n                    return True'
)

# 3. Add language dropdown in admin settings page
# Find "Login Type" section and add language after it
content = content.replace(
    '        lt_combo = Gtk.ComboBoxText()\n'
    '        lt_combo.append_text("DEFAULT")\n'
    '        lt_combo.append_text("EXTERNAL")\n'
    '        lt_combo.set_active(0 if LOGIN_TYPE == "DEFAULT" else 1)\n'
    '        box.pack_start(lt_combo, False, False, 0)',

    '        lt_combo = Gtk.ComboBoxText()\n'
    '        lt_combo.append_text("DEFAULT")\n'
    '        lt_combo.append_text("EXTERNAL")\n'
    '        lt_combo.set_active(0 if LOGIN_TYPE == "DEFAULT" else 1)\n'
    '        box.pack_start(lt_combo, False, False, 0)\n'
    '\n'
    '        # TTS Language\n'
    '        lang_l = Gtk.Label(label="Announcement Language")\n'
    '        lang_l.modify_font(Pango.FontDescription("Sans bold 11"))\n'
    '        lang_l.set_halign(Gtk.Align.START)\n'
    '        box.pack_start(lang_l, False, False, 0)\n'
    '        lang_combo = Gtk.ComboBoxText()\n'
    '        lang_combo.append_text("English (Indian)")\n'
    '        lang_combo.append_text("Telugu")\n'
    '        lang_combo.append_text("Hindi")\n'
    '        lang_combo.append_text("Kannada")\n'
    '        lang_combo.append_text("Tamil")\n'
    '        lang_map = {"en": 0, "te": 1, "hi": 2, "kn": 3, "ta": 4}\n'
    '        lang_combo.set_active(lang_map.get(TTS_LANG, 0))\n'
    '        box.pack_start(lang_combo, False, False, 0)'
)

# 4. Update on_save to save language
content = content.replace(
    '            if save_admin_config(new_user, new_pass, new_lt):',
    '            lang_options = ["en", "te", "hi", "kn", "ta"]\n'
    '            new_lang = lang_options[lang_combo.get_active()]\n'
    '            global TTS_LANG\n'
    '            TTS_LANG = new_lang\n'
    '            if save_admin_config(new_user, new_pass, new_lt, new_lang):'
)

# 5. Replace all hardcoded lang="en", tld="co.in" with TTS_LANG
content = content.replace(
    'tts = gTTS(text=text, lang="en", tld="co.in")',
    'tts = gTTS(text=text, lang=TTS_LANG, tld="co.in")'
)

# 6. Add _set_api_creds to also set TTS_LANG
content = content.replace(
    '    def _set_api_creds(self, user, passwd, lt):\n'
    '        global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time',
    '    def _set_api_creds(self, user, passwd, lt):\n'
    '        global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time, TTS_LANG'
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Verify syntax
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
