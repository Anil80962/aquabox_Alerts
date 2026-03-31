import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Problem: typing speed is fixed at 100ms but audio length varies
# Solution: calculate typing speed dynamically based on audio duration
# Each WAV file duration = file_size / (sample_rate * channels * bytes_per_sample)
# For 44100Hz, 1ch, 16bit: duration = size / (44100 * 1 * 2)

# Replace fixed typing speed with dynamic speed calculation
# Add a method to calculate and set typing speed per alert

old_start = '''    def _start_typing(self, text):
        """Start typing animation."""
        self._typing_done = False
        self._typing_text = "\\U0001F50A ANNOUNCING: " + text
        self._typing_index = 0'''

new_start = '''    def _start_typing(self, text, duration=0):
        """Start typing animation. duration=estimated audio seconds."""
        self._typing_done = False
        self._typing_text = "\\U0001F50A ANNOUNCING: " + text
        self._typing_index = 0
        # Calculate speed: text must finish in 'duration' seconds
        # If no duration given, use 60 WPM default
        total_chars = len(self._typing_text)
        if duration > 0 and total_chars > 0:
            self._typing_speed = max(10, int((duration * 1000) / total_chars))
        else:
            self._typing_speed = 100  # default 60 WPM'''

content = content.replace(old_start, new_start)

# Use dynamic speed in timer
content = content.replace(
    'self._typing_timer = GLib.timeout_add(100, self._typing_tick)',
    'self._typing_timer = GLib.timeout_add(self._typing_speed, self._typing_tick)'
)

# Add _typing_speed default in init
content = content.replace(
    '        self._typing_done = True',
    '        self._typing_done = True\n        self._typing_speed = 100'
)

# In announce_all play loop - get audio duration and pass to _start_typing
old_play_typing = '''                # Start typing animation
                GLib.idle_add(self._start_typing, texts[i])
                time.sleep(0.1)  # Tiny wait for typing to render

                # Start audio in a subprocess (non-blocking)
                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:2,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)'''

new_play_typing = '''                # Get audio duration to sync typing speed
                audio_duration = 0
                try:
                    fsize = os.path.getsize(audio_files[i])
                    audio_duration = fsize / (44100 * 2)  # 44100Hz, 16bit mono
                except:
                    audio_duration = 5

                # Start typing animation with matched speed
                GLib.idle_add(self._start_typing, texts[i], audio_duration)
                time.sleep(0.1)

                # Start audio
                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:2,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)'''

content = content.replace(old_play_typing, new_play_typing)

# Also fix single announce (_on_announce) to pass duration
old_single = '''                GLib.idle_add(self._start_typing, text)
                subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)'''

new_single = '''                audio_dur = 0
                try:
                    audio_dur = os.path.getsize(wav_path) / (44100 * 2)
                except:
                    audio_dur = 5
                GLib.idle_add(self._start_typing, text, audio_dur)
                subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)'''

# Replace all occurrences
content = content.replace(old_single, new_single)

# Fix auto_announce_unread too
old_auto = '''                GLib.idle_add(self._start_typing, text)
                subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                # Wait for typing to finish
                for _ in range(200):
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.02)
                time.sleep(0.5)'''

new_auto = '''                audio_dur = 0
                try:
                    audio_dur = os.path.getsize(wav_path) / (44100 * 2)
                except:
                    audio_dur = 5
                GLib.idle_add(self._start_typing, text, audio_dur)
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
