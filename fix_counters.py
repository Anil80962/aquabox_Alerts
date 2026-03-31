import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add instant counter update method
NEW_METHOD = '''    def _update_counters(self, delta):
        """Instantly update unread/read counters."""
        try:
            cur_unread = int(self.stat_unread[1].get_text())
            cur_read = int(self.stat_read[1].get_text())
            self.stat_unread[1].set_text(str(max(0, cur_unread - delta)))
            self.stat_read[1].set_text(str(cur_read + delta))
        except Exception:
            pass

'''

content = content.replace(
    '    def _make_stat(self, num, label, css_class):',
    NEW_METHOD + '    def _make_stat(self, num, label, css_class):'
)

# 2. Update auto_announce_unread - add counter update after each alert
old_auto = "            announce_and_mark_read(alert)\n            time.sleep(0.5)"
new_auto = "            announce_and_mark_read(alert)\n            GLib.idle_add(self._update_counters, 1)\n            time.sleep(0.5)"
content = content.replace(old_auto, new_auto, 1)  # Only first occurrence (in _auto_announce_unread)

# 3. Update _after_announce - add counter update
old_after = '        button.set_label("\\u25CF  Announced")\n        button.set_sensitive(True)\n\n    def _on_mark_read'
new_after = '        button.set_label("\\u25CF  Announced")\n        button.set_sensitive(True)\n        self._update_counters(1)\n\n    def _on_mark_read'
content = content.replace(old_after, new_after)

# 4. Update _after_mark_read - add counter update
old_mark = '        button.set_label("\\u25CF  Done")\n        button.set_sensitive(True)\n\n    def _on_announce'
new_mark = '        button.set_label("\\u25CF  Done")\n        button.set_sensitive(True)\n        self._update_counters(1)\n\n    def _on_announce'
content = content.replace(old_mark, new_mark)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('rm -f /home/aquabox/Desktop/Aquabox/user_session.json')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
