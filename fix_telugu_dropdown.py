import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

# 1. Install Telugu/Indic fonts
stdin, stdout, stderr = ssh.exec_command(
    'echo "aquabox@2026" | sudo -S apt-get install -y fonts-telugu fonts-noto fonts-noto-cjk fonts-indic 2>&1 | tail -5',
    timeout=120
)
time.sleep(30)
print('Fonts:', stdout.read().decode('utf-8', errors='replace').strip())

# 2. Fix the language button to be a dropdown instead of cycle button
sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Remove old language cycle button
old_lang_btn = (
    '        # Language toggle button\n'
    '        self._lang_list = ["en", "te", "kn", "ta", "hi", "ml"]\n'
    '        self._lang_labels = ["ENG", "TEL", "KAN", "TAM", "HIN", "MAL"]\n'
    '        self._lang_idx = 0\n'
    '        for i, l in enumerate(self._lang_list):\n'
    '            if l == TTS_LANG:\n'
    '                self._lang_idx = i\n'
    '                break\n'
    '        self.lang_btn = Gtk.Button(label=self._lang_labels[self._lang_idx])\n'
    '        self.lang_btn.modify_font(Pango.FontDescription("Sans bold 10"))\n'
    '        self.lang_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.9))\n'
    '        self.lang_btn.get_style_context().add_class("refresh-btn")\n'
    '        self.lang_btn.connect("clicked", self._toggle_lang)\n'
    '        right_box.pack_start(self.lang_btn, False, False, 0)'
)

new_lang_dropdown = (
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
    '        right_box.pack_start(self.lang_combo, False, False, 0)'
)

content = content.replace(old_lang_btn, new_lang_dropdown)

# Replace _toggle_lang with _on_lang_changed
old_toggle = (
    '    def _toggle_lang(self, button):\n'
    '        global TTS_LANG\n'
    '        self._lang_idx = (self._lang_idx + 1) % len(self._lang_list)\n'
    '        TTS_LANG = self._lang_list[self._lang_idx]\n'
    '        button.set_label(self._lang_labels[self._lang_idx])\n'
)

new_changed = (
    '    def _on_lang_changed(self, combo):\n'
    '        global TTS_LANG\n'
    '        idx = combo.get_active()\n'
    '        TTS_LANG = self._lang_list[idx]\n'
)

content = content.replace(old_toggle, new_changed)

# 3. Fix overlay label font to support Telugu/Indic scripts
content = content.replace(
    'self.overlay_label.modify_font(Pango.FontDescription("monospace bold 14"))',
    'self.overlay_label.modify_font(Pango.FontDescription("Noto Sans bold 14"))'
)

# Also fix announce bar label font
content = content.replace(
    'self.announce_label.get_style_context().add_class("announce-text")',
    'self.announce_label.get_style_context().add_class("announce-text")\n'
    '        self.announce_label.modify_font(Pango.FontDescription("Noto Sans bold 13"))'
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
    # Rebuild font cache
    ssh.exec_command('fc-cache -f 2>/dev/null')
    time.sleep(2)
    ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
    ssh.exec_command('killall aplay 2>/dev/null')
    time.sleep(2)
    ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
    print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
