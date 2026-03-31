import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Remove language from admin page
content = content.replace(
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
    '        lang_combo.append_text("Malayalam")\n'
    '        lang_map = {"en": 0, "te": 1, "hi": 2, "kn": 3, "ta": 4, "ml": 5}\n'
    '        lang_combo.set_active(lang_map.get(TTS_LANG, 0))\n'
    '        box.pack_start(lang_combo, False, False, 0)',
    '        # Language selection moved to header bar dropdown'
)

# Remove lang_combo references in admin save
content = content.replace(
    '            lang_options = ["en", "te", "hi", "kn", "ta", "ml"]\n'
    '            new_lang = lang_options[lang_combo.get_active()]\n'
    '            global TTS_LANG\n'
    '            TTS_LANG = new_lang\n'
    '            if save_admin_config(new_user, new_pass, new_lt, new_lang):',
    '            if save_admin_config(new_user, new_pass, new_lt, TTS_LANG):'
)

# 2. Add CSS for the header dropdown to blend with header bar
css_addition = '''
.header-lang {
    background: rgba(255,255,255,0.15);
    color: white;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 11px;
    min-height: 22px;
}
'''

# Find the CSS section and add
content = content.replace(
    '.refresh-btn {',
    css_addition + '\n.refresh-btn {'
)

# 3. Style the dropdown and make it smaller
content = content.replace(
    '        # Language dropdown\n'
    '        self._lang_list = ["en", "te", "kn", "ta", "hi", "ml"]\n'
    '        self.lang_combo = Gtk.ComboBoxText()\n'
    '        self.lang_combo.append_text("ENG")\n'
    '        self.lang_combo.append_text("TEL")\n'
    '        self.lang_combo.append_text("KAN")\n'
    '        self.lang_combo.append_text("TAM")\n'
    '        self.lang_combo.append_text("HIN")\n'
    '        self.lang_combo.append_text("MAL")\n'
    '        lang_idx = 0\n'
    '        for i, l in enumerate(self._lang_list):\n'
    '            if l == TTS_LANG:\n'
    '                lang_idx = i\n'
    '                break\n'
    '        self.lang_combo.set_active(lang_idx)\n'
    '        self.lang_combo.connect("changed", self._on_lang_changed)\n'
    '        right_box.pack_start(self.lang_combo, False, False, 0)',

    '        # Language dropdown\n'
    '        self._lang_list = ["en", "te", "kn", "ta", "hi", "ml"]\n'
    '        self.lang_combo = Gtk.ComboBoxText()\n'
    '        self.lang_combo.append_text("ENG")\n'
    '        self.lang_combo.append_text("TEL")\n'
    '        self.lang_combo.append_text("KAN")\n'
    '        self.lang_combo.append_text("TAM")\n'
    '        self.lang_combo.append_text("HIN")\n'
    '        self.lang_combo.append_text("MAL")\n'
    '        lang_idx = 0\n'
    '        for i, l in enumerate(self._lang_list):\n'
    '            if l == TTS_LANG:\n'
    '                lang_idx = i\n'
    '                break\n'
    '        self.lang_combo.set_active(lang_idx)\n'
    '        self.lang_combo.get_style_context().add_class("header-lang")\n'
    '        self.lang_combo.set_size_request(60, 24)\n'
    '        self.lang_combo.connect("changed", self._on_lang_changed)\n'
    '        right_box.pack_start(self.lang_combo, False, False, 0)'
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
