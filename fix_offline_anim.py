import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Replace the offline do_offline inner function with proper animation + audio sync
old_offline = '''        def do_offline():
            import subprocess
            _start_announcing()
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = f"Offline unit {i+1} of {len(alerts)}. {title}. {status}"

                try:
                    aid = alert.get("id", "")
                    wav_path = _audio_cache.get(aid)
                    if not wav_path or not os.path.exists(wav_path):
                        from gtts import gTTS
                        mp3_path = "/tmp/aquabox_offline_ann.mp3"
                        wav_path = "/tmp/aquabox_offline_ann.wav"
                        if _announce_stop: break
                    if _announce_stop: break
                    tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", wav_path], capture_output=True, timeout=30)
                    time.sleep(1)
                except Exception as e:
                    print(f"[{now()}] Offline announce error: {e}")
                time.sleep(0.5)

            _stop_announcing()
            GLib.idle_add(self._after_announce_offline, button)'''

new_offline = '''        def do_offline():
            import subprocess
            _start_announcing()
            self._batch_announcing = True
            total = len(alerts)

            # Pre-generate all audio
            GLib.idle_add(button.set_label, "Generating audio...")
            audio_files = []
            texts = []
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = "Offline unit " + str(i+1) + " of " + str(total) + ". " + title + ". " + status
                texts.append(text)
                try:
                    from gtts import gTTS
                    mp3_path = "/tmp/offline_" + str(i) + ".mp3"
                    wav_path = "/tmp/offline_" + str(i) + ".wav"
                    if _announce_stop: pass  # cancelled
                    tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)
                    audio_files.append(wav_path)
                except Exception as e:
                    audio_files.append(None)

            # Play each with animation
            GLib.idle_add(button.set_label, "Playing offline alerts...")
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                if i >= len(audio_files) or not audio_files[i]:
                    continue

                audio_duration = 0
                try:
                    audio_duration = os.path.getsize(audio_files[i]) / (44100 * 2)
                except:
                    audio_duration = 5

                self._typing_done = False
                GLib.idle_add(self._start_typing, texts[i], audio_duration)
                time.sleep(0.3)

                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:0,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while audio_proc.poll() is None:
                    if _announce_stop:
                        audio_proc.kill()
                        break
                    time.sleep(0.1)

                for _ in range(100):
                    if self._typing_done or _announce_stop:
                        break
                    time.sleep(0.01)

                time.sleep(0.5)

            self._batch_announcing = False
            _stop_announcing()
            GLib.idle_add(self._after_announce_offline, button)'''

content = content.replace(old_offline, new_offline)

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
