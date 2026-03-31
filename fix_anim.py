import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Wider overlay text
content = content.replace(
    'self.overlay_label.set_max_width_chars(50)',
    'self.overlay_label.set_max_width_chars(80)'
)

# 2. Reset _typing_done BEFORE idle_add in announce_all
content = content.replace(
    '                GLib.idle_add(self._start_typing, texts[i], audio_duration)\n                time.sleep(0.1)',
    '                self._typing_done = False\n                GLib.idle_add(self._start_typing, texts[i], audio_duration)\n                time.sleep(0.3)'
)

# 3. Ensure overlay is forced visible in _start_typing
# Add extra show calls after the initial text set
old_force = '        self.overlay_label.set_text("\\U0001F50A ...")'
new_force = (
    '        self.overlay_label.set_text("\\U0001F50A ...")\n'
    '        self.overlay_container.set_visible(True)\n'
    '        self.overlay_container.show_all()\n'
    '        self.overlay_label.show()'
)
content = content.replace(old_force, new_force)

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
