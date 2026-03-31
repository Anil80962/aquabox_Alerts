import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add a global announcing lock
content = content.replace(
    '_announce_stop = False  # Flag to stop announcing',
    '_announce_stop = False  # Flag to stop announcing\n'
    '_announcing = False  # Only one announce at a time'
)

# 2. Add helper to check/set announcing state
content = content.replace(
    'def precache_audio(alerts):',
    'def _start_announcing():\n'
    '    global _announcing, _announce_stop\n'
    '    if _announcing:\n'
    '        # Stop current announce first\n'
    '        _announce_stop = True\n'
    '        import subprocess\n'
    '        subprocess.run(["killall", "aplay"], capture_output=True)\n'
    '        import time\n'
    '        time.sleep(0.5)\n'
    '    _announce_stop = False\n'
    '    _announcing = True\n'
    '    return True\n'
    '\n'
    'def _stop_announcing():\n'
    '    global _announcing\n'
    '    _announcing = False\n'
    '\n'
    'def precache_audio(alerts):'
)

# 3. Wrap all do_all/do_announce/do_offline/auto_announce with the lock

# Fix announce all - do_all
content = content.replace(
    '        def do_all():\n            import subprocess\n            global _announce_stop\n            _announce_stop = False',
    '        def do_all():\n            import subprocess\n            _start_announcing()'
)

# Fix single announce - do_announce
content = content.replace(
    '        def do_announce():\n            global _announce_stop\n            _announce_stop = False',
    '        def do_announce():\n            _start_announcing()'
)

# Fix auto_announce_unread
content = content.replace(
    '    def _auto_announce_unread(self, alerts):\n        """Auto-announce unread alerts one by one."""\n        import subprocess\n        global _announce_stop\n        _announce_stop = False',
    '    def _auto_announce_unread(self, alerts):\n        """Auto-announce unread alerts one by one."""\n        import subprocess\n        _start_announcing()'
)

# Fix auto_announce_offline_timer
content = content.replace(
    '        def do_offline_auto():\n            import subprocess\n            global _announce_stop\n            _announce_stop = False',
    '        def do_offline_auto():\n            import subprocess\n            _start_announcing()'
)

# Fix _on_announce_offline
content = content.replace(
    '        def do_offline():\n            import subprocess\n            global _announce_stop\n            _announce_stop = False',
    '        def do_offline():\n            import subprocess\n            _start_announcing()'
)

# 4. Add _stop_announcing at the end of each announce function

# After announce_all finishes
content = content.replace(
    '            self._batch_announcing = False\n            GLib.idle_add(self._after_announce_all, button)',
    '            self._batch_announcing = False\n            _stop_announcing()\n            GLib.idle_add(self._after_announce_all, button)'
)

# After single announce finishes - find the line before _after_announce
content = content.replace(
    '            GLib.idle_add(self._after_announce, button)\n        threading.Thread(target=do_announce',
    '            _stop_announcing()\n            GLib.idle_add(self._after_announce, button)\n        threading.Thread(target=do_announce'
)

# After auto_announce_unread
old_auto_end = '        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")'
content = content.replace(
    old_auto_end,
    old_auto_end + '\n        _stop_announcing()'
)

# After offline auto
content = content.replace(
    '        threading.Thread(target=do_offline_auto, daemon=True).start()\n        return True',
    '        threading.Thread(target=do_offline_auto, daemon=True).start()\n        return True  # Keep timer'
)

# After _on_announce_offline
content = content.replace(
    '            GLib.idle_add(self._after_announce_offline, button)\n\n        threading.Thread(target=do_offline',
    '            _stop_announcing()\n            GLib.idle_add(self._after_announce_offline, button)\n\n        threading.Thread(target=do_offline'
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
ssh.exec_command('killall aplay 2>/dev/null')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command('journalctl -u aquabox-alerts.service --no-pager -n 3 2>&1 | grep -i error | grep -v AT-SPI | grep -v Deprecation')
err = stdout.read().decode('utf-8', errors='replace').strip()
print('Errors:', err if err else 'None')

ssh.close()
print('Done!')
