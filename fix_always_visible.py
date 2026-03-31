import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Always visible
content = content.replace(
    '        self._panda_visible = False',
    '        self._panda_visible = True'
)
content = content.replace(
    '        self._panda_alpha = 0.0',
    '        self._panda_alpha = 1.0'
)

# 2. Remove no_show_all and set_visible(False)
content = content.replace(
    '        self._panda_da.set_no_show_all(True)\n        self._panda_da.set_visible(False)',
    '        # Always visible on screen'
)

# 3. Change timer from show every 60s to change message every 10s
content = content.replace(
    '        GLib.timeout_add_seconds(60, self._show_panda)',
    '        GLib.timeout_add_seconds(10, self._change_panda_msg)'
)

# 4. Set initial message
content = content.replace(
    "        self._panda_current_msg = \"\"",
    "        self._panda_current_msg = self._panda_messages[0]"
)

# 5. Add _change_panda_msg method before _show_panda
content = content.replace(
    '    def _show_panda(self):',
    '    def _change_panda_msg(self):\n'
    '        """Change message every 10 seconds."""\n'
    '        self._panda_msg_idx += 1\n'
    '        self._panda_msg_char = 0\n'
    '        self._panda_current_msg = self._panda_messages[self._panda_msg_idx % len(self._panda_messages)]\n'
    '        return True\n\n'
    '    def _show_panda(self):'
)

# 6. Keep alpha always 1.0 in animate
content = content.replace(
    '            if self._panda_alpha < 1.0:\n                self._panda_alpha = min(1.0, self._panda_alpha + 0.05)',
    '            self._panda_alpha = 1.0'
)

# 7. Remove auto-hide in _show_panda
content = content.replace(
    "        # Auto-hide after 8 seconds\n        GLib.timeout_add_seconds(8, self._hide_panda)",
    "        pass"
)

# 8. Disable fade out
content = content.replace(
    '    def _hide_panda(self):\n        self._panda_visible = False\n        GLib.timeout_add(50, self._fade_panda_out)\n        return False',
    '    def _hide_panda(self):\n        return False'
)

content = content.replace(
    '    def _fade_panda_out(self):\n        self._panda_alpha -= 0.05\n        if self._panda_alpha <= 0:\n            self._panda_da.set_visible(False)\n            self._panda_da.hide()\n            return False\n        self._panda_da.queue_draw()\n        return True',
    '    def _fade_panda_out(self):\n        return False'
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
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
