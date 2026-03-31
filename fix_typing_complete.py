import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Add a typing_done flag
content = content.replace(
    "        self._typing_timer = None\n        self._hide_timer = None",
    "        self._typing_timer = None\n        self._hide_timer = None\n        self._typing_done = True"
)

# Set typing_done = False when typing starts
content = content.replace(
    '    def _start_typing(self, text):\n        """Start typing animation."""',
    '    def _start_typing(self, text):\n        """Start typing animation."""\n        self._typing_done = False'
)

# Set typing_done = True when typing finishes
content = content.replace(
    '            self.overlay_label.set_text(self._typing_text + "  \\u2713")',
    '            self.overlay_label.set_text(self._typing_text + "  \\u2713")\n            self._typing_done = True'
)

# In the announce all play loop - wait for BOTH audio AND typing to finish
old_play = '''                # Start audio in a subprocess (non-blocking)
                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:2,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Wait for audio to finish completely
                audio_proc.wait()

                # Audio done - mark as read
                if not _announce_stop:
                    announce_and_mark_read(alert)
                    GLib.idle_add(self._update_counters, 1)

                # Pause between alerts
                time.sleep(0.5)'''

new_play = '''                # Start audio in a subprocess (non-blocking)
                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:2,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Wait for audio to finish completely
                audio_proc.wait()

                # Wait for typing animation to also finish
                for _ in range(200):  # Max 4 seconds wait
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.02)

                # Both done - mark as read
                if not _announce_stop:
                    announce_and_mark_read(alert)
                    GLib.idle_add(self._update_counters, 1)

                # Pause between alerts
                time.sleep(1)'''

content = content.replace(old_play, new_play)

# Also fix single announce and auto_announce_unread the same way
# For auto_announce_unread
old_auto = '''                GLib.idle_add(self._start_typing, text)
                subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                time.sleep(1)'''

new_auto = '''                GLib.idle_add(self._start_typing, text)
                subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                # Wait for typing to finish
                for _ in range(200):
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.02)
                time.sleep(0.5)'''

content = content.replace(old_auto, new_auto)

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
