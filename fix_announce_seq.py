import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Replace do_all with strictly sequential: generate -> show typing -> play audio -> WAIT -> next
old = '''        def do_all():
            import subprocess
            global _announce_stop
            _announce_stop = False
            total = len(alerts)
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                body = alert.get("body", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = "Alert " + str(i+1) + " of " + str(total) + ". " + title + ". " + body + ". " + status

                try:
                    from gtts import gTTS
                    # Use unique file per alert to avoid overwrite
                    mp3_path = "/tmp/announce_all_" + str(i) + ".mp3"
                    wav_path = "/tmp/announce_all_" + str(i) + ".wav"
                    tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=30)
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                    time.sleep(0.5)
                except Exception as e:
                    print("[" + now() + "] Announce all error: " + str(e))

                if not _announce_stop:
                    announce_and_mark_read(alert)
                    GLib.idle_add(self._update_counters, 1)
                time.sleep(0.3)

            GLib.idle_add(self._after_announce_all, button)'''

new = '''        def do_all():
            import subprocess
            global _announce_stop
            _announce_stop = False
            total = len(alerts)

            # Step 1: Pre-generate ALL audio files first
            GLib.idle_add(button.set_label, "Generating audio...")
            audio_files = []
            texts = []
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                body = alert.get("body", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = "Alert " + str(i+1) + " of " + str(total) + ". " + title + ". " + body + ". " + status
                texts.append(text)

                try:
                    from gtts import gTTS
                    mp3_path = "/tmp/announce_all_" + str(i) + ".mp3"
                    wav_path = "/tmp/announce_all_" + str(i) + ".wav"
                    tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=30)
                    audio_files.append(wav_path)
                except Exception as e:
                    print("[" + now() + "] Audio gen error: " + str(e))
                    audio_files.append(None)

            # Step 2: Play each one sequentially - typing + audio together, wait for finish
            GLib.idle_add(button.set_label, "Playing alerts...")
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                if i >= len(audio_files) or not audio_files[i]:
                    continue

                # Show typing animation
                GLib.idle_add(self._start_typing, texts[i])

                # Play audio - this BLOCKS until audio finishes
                result = subprocess.run(["aplay", "-D", "plughw:2,0", "-q", audio_files[i]], capture_output=True, timeout=60)

                # Audio done - mark as read
                if not _announce_stop:
                    announce_and_mark_read(alert)
                    GLib.idle_add(self._update_counters, 1)

                # Small pause between alerts
                time.sleep(1)

            GLib.idle_add(self._after_announce_all, button)'''

content = content.replace(old, new)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
