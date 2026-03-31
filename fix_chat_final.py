import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# The problem: _add_bot_message was called with 3 args (self, text, True)
# but the idle_add passes them differently
# Fix: change the send_chat to not pass speak as positional

content = content.replace(
    '            answer = self._get_ai_answer(text)\n'
    '            GLib.idle_add(self._add_bot_message, answer, True)',
    '            answer = self._get_ai_answer(text)\n'
    '            GLib.idle_add(self._add_bot_reply, answer)'
)

# Add _add_bot_reply that calls _add_bot_message with speak=True
content = content.replace(
    '    def _chat_typing_tick(self):',
    '    def _add_bot_reply(self, text):\n'
    '        self._add_bot_message(text, speak=True)\n'
    '\n'
    '    def _chat_typing_tick(self):'
)

# Also fix the scroll_chat_bottom error
content = content.replace(
    '    def _scroll_chat_bottom(self):\n'
    '        adj = self._chat_box.get_parent().get_vadjustment()\n'
    '        adj.set_value(adj.get_upper())\n'
    '        return False',
    '    def _scroll_chat_bottom(self):\n'
    '        try:\n'
    '            adj = self._chat_box.get_parent().get_vadjustment()\n'
    '            adj.set_value(adj.get_upper())\n'
    '        except: pass\n'
    '        return False'
)

# Replace bot avatar with Fluxgen icon image
content = content.replace(
    '        # Bot avatar - water drop image\n'
    '        logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"',
    '        # Bot avatar - Fluxgen icon\n'
    '        logo_path = "/home/aquabox/Desktop/Aquabox/fluxgen-icon.jpg"'
)

# Also use fluxgen icon in chat header
content = content.replace(
    '        # Logo in header\n'
    '        logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"',
    '        # Logo in header\n'
    '        logo_path = "/home/aquabox/Desktop/Aquabox/fluxgen-icon.jpg"'
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
