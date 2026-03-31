import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# The problem: _typing_tick finishes, sets a 4-second hide timer
# But the next alert starts typing within those 4 seconds
# The hide timer fires and hides the NEW alert's typing

# Fix: In _start_typing, cancel BOTH the typing timer AND the hide timer
# Currently it only cancels _typing_timer

old_cancel = '''        # Cancel any pending hide timer from previous alert
        if self._hide_timer:
            try:
                GLib.source_remove(self._hide_timer)
            except Exception:
                pass
            self._hide_timer = None'''

# Check if this code exists
if old_cancel in content:
    print("Found existing hide_timer cancel")
else:
    print("hide_timer cancel NOT found - adding it")
    # Add it at the start of _start_typing, after _typing_done = False
    content = content.replace(
        '        self._typing_done = False\n        self._typing_text =',
        '        self._typing_done = False\n'
        '        # Cancel any pending hide timer from previous alert\n'
        '        if self._hide_timer:\n'
        '            try:\n'
        '                GLib.source_remove(self._hide_timer)\n'
        '            except Exception:\n'
        '                pass\n'
        '            self._hide_timer = None\n'
        '        # Cancel any running typing timer\n'
        '        if self._typing_timer:\n'
        '            try:\n'
        '                GLib.source_remove(self._typing_timer)\n'
        '            except Exception:\n'
        '                pass\n'
        '            self._typing_timer = None\n'
        '        self._typing_text ='
    )

# Also remove the duplicate cancel block that may exist later in _start_typing
# Check for existing cancel code
old_dup = '''        if self._typing_timer:
            try:
                GLib.source_remove(self._typing_timer)
            except Exception:
                pass
            self._typing_timer = None

        print'''

new_dup = '''        print'''

if old_dup in content:
    content = content.replace(old_dup, new_dup)
    print("Removed duplicate cancel block")

# Also: don't auto-hide after typing complete during announce-all
# Change the hide timer to only fire for single announce, not during batch
# Add a flag for batch mode
content = content.replace(
    '        self._typing_done = True\n        self._typing_speed = 100',
    '        self._typing_done = True\n        self._typing_speed = 100\n        self._batch_announcing = False'
)

# Set batch mode in announce_all
content = content.replace(
    '            GLib.idle_add(button.set_label, "Playing alerts...")',
    '            self._batch_announcing = True\n            GLib.idle_add(button.set_label, "Playing alerts...")'
)

# Clear batch mode after announce_all
content = content.replace(
    '            GLib.idle_add(self._after_announce_all, button)',
    '            self._batch_announcing = False\n            GLib.idle_add(self._after_announce_all, button)'
)

# Don't set hide timer during batch mode
content = content.replace(
    '            self._hide_timer = GLib.timeout_add(4000, self._hide_announce_overlay)',
    '            if not self._batch_announcing:\n                self._hide_timer = GLib.timeout_add(4000, self._hide_announce_overlay)'
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
