import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add a refresh queue flag
content = content.replace(
    "_auto_announcing = False  # Prevent overlapping auto-announce",
    "_auto_announcing = False  # Prevent overlapping auto-announce\n"
    "_refresh_queued = False  # Queue refresh if announce is running"
)

# 2. Modify _fetch_and_update to check if announce is running
# If announcing, queue the refresh instead of running it
old_fetch = '''    def _fetch_and_update(self):
        # Prevent fetching more than once every 30 seconds
        now_ts = time.time()
        if now_ts - self._last_fetch_time_actual < 30:
            return
        self._last_fetch_time_actual = now_ts'''

new_fetch = '''    def _fetch_and_update(self):
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
        self._last_fetch_time_actual = now_ts'''

content = content.replace(old_fetch, new_fetch)

# 3. After auto-announce finishes, check if refresh was queued
old_auto_end = '        _auto_announcing = False\n        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")'

new_auto_end = (
    '        _auto_announcing = False\n'
    '        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")\n'
    '        # Process queued refresh\n'
    '        global _refresh_queued\n'
    '        if _refresh_queued:\n'
    '            _refresh_queued = False\n'
    '            print("[" + now() + "] Processing queued refresh")\n'
    '            time.sleep(1)\n'
    '            GLib.idle_add(self.refresh_alerts)'
)

content = content.replace(old_auto_end, new_auto_end)

# 4. Also check queue after Announce All finishes
content = content.replace(
    '            self._batch_announcing = False\n            _stop_announcing()\n            GLib.idle_add(self._after_announce_all, button)',
    '            self._batch_announcing = False\n'
    '            _stop_announcing()\n'
    '            # Process queued refresh\n'
    '            if _refresh_queued:\n'
    '                _refresh_queued = False\n'
    '                time.sleep(1)\n'
    '                GLib.idle_add(self.refresh_alerts)\n'
    '            GLib.idle_add(self._after_announce_all, button)'
)

# 5. Also check queue after offline announce finishes
content = content.replace(
    '            self._batch_announcing = False\n            _stop_announcing()\n            GLib.idle_add(self._after_announce_offline, button)',
    '            self._batch_announcing = False\n'
    '            _stop_announcing()\n'
    '            if _refresh_queued:\n'
    '                _refresh_queued = False\n'
    '                time.sleep(1)\n'
    '                GLib.idle_add(self.refresh_alerts)\n'
    '            GLib.idle_add(self._after_announce_offline, button)'
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
