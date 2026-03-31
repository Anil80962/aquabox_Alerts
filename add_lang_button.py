import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Add language button in the header bar - between refresh and separator
# Find where refresh button is added
content = content.replace(
    '        right_box.pack_start(self.refresh_btn, False, False, 0)',
    '        right_box.pack_start(self.refresh_btn, False, False, 0)\n'
    '\n'
    '        # Language toggle button\n'
    '        self._lang_list = ["en", "te", "kn", "ta"]\n'
    '        self._lang_labels = ["ENG", "TEL", "KAN", "TAM"]\n'
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

# Add _toggle_lang method
content = content.replace(
    '    def on_refresh_clicked(self, button):',
    '    def _toggle_lang(self, button):\n'
    '        global TTS_LANG\n'
    '        self._lang_idx = (self._lang_idx + 1) % len(self._lang_list)\n'
    '        TTS_LANG = self._lang_list[self._lang_idx]\n'
    '        button.set_label(self._lang_labels[self._lang_idx])\n'
    '        # Save to admin config\n'
    '        try:\n'
    '            import json\n'
    '            if os.path.exists(ADMIN_CONFIG):\n'
    '                with open(ADMIN_CONFIG) as f:\n'
    '                    cfg = json.load(f)\n'
    '                cfg["tts_lang"] = TTS_LANG\n'
    '                with open(ADMIN_CONFIG, "w") as f:\n'
    '                    json.dump(cfg, f)\n'
    '        except: pass\n'
    '        # Clear audio cache for new language\n'
    '        _audio_cache.clear()\n'
    '\n'
    '    def on_refresh_clicked(self, button):'
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
