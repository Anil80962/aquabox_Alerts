import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Strategy: Track which alert IDs have been announced already
# Only announce NEW unread alerts that haven't been announced before
# This prevents re-reading on every refresh

# 1. Add a set to track announced IDs
content = content.replace(
    "_announce_stop = False  # Flag to stop announcing",
    "_announce_stop = False  # Flag to stop announcing\n"
    "_announced_ids = set()  # Track already-announced alert IDs\n"
    "_auto_announcing = False  # Prevent overlapping auto-announce"
)

# 2. Replace the pass with smart auto-announce
content = content.replace(
    "                pass  # No auto-announce - use buttons",
    "                # Auto-announce only NEW unread alerts (not already announced)\n"
    "                new_unread = [a for a in unread_alerts if a.get('id','') not in _announced_ids]\n"
    "                if new_unread and not _auto_announcing:\n"
    "                    threading.Thread(target=self._auto_announce_unread, args=(list(new_unread),), daemon=True).start()"
)

# 3. Fix _auto_announce_unread to use _auto_announcing flag and track IDs
old_auto = (
    '    def _auto_announce_unread(self, alerts):\n'
    '        """Auto-announce unread alerts one by one."""\n'
    '        import subprocess\n'
    '        _start_announcing()'
)

new_auto = (
    '    def _auto_announce_unread(self, alerts):\n'
    '        """Auto-announce unread alerts one by one."""\n'
    '        global _auto_announcing, _announced_ids\n'
    '        if _auto_announcing:\n'
    '            return\n'
    '        _auto_announcing = True\n'
    '        import subprocess\n'
    '        _start_announcing()'
)

content = content.replace(old_auto, new_auto)

# 4. Add alert ID to _announced_ids after each announce
content = content.replace(
    '            announce_and_mark_read(alert)\n'
    '            GLib.idle_add(self._update_counters, 1)\n'
    '            time.sleep(0.5)\n'
    '\n'
    '        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")',

    '            _announced_ids.add(alert.get("id", ""))\n'
    '            announce_and_mark_read(alert)\n'
    '            GLib.idle_add(self._update_counters, 1)\n'
    '            time.sleep(0.5)\n'
    '\n'
    '        _auto_announcing = False\n'
    '        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")'
)

# 5. Clear _auto_announcing on cancel
content = content.replace(
    "        global _announce_stop\n        _announce_stop = True",
    "        global _announce_stop, _auto_announcing\n        _announce_stop = True\n        _auto_announcing = False"
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
