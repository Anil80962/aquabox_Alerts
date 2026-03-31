import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Replace the entire do_all function inside _on_announce_all
old_do_all = '''        def do_all():
            import subprocess
            global _announce_stop
            _announce_stop = False
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    print(f"[{now()}] Announce all cancelled at alert {i+1}")
                    break
                title = alert.get("title", "")
                body = alert.get("body", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = f"Alert {i+1} of {len(alerts)}. {title}. {body}. {status}"

                # Generate audio first
                try:
                    aid = alert.get("id", "")
                    wav_path = _audio_cache.get(aid)
                    if not wav_path or not os.path.exists(wav_path):
                        from gtts import gTTS
                        mp3_path = "/tmp/aquabox_announce_all.mp3"
                        wav_path = "/tmp/aquabox_announce_all.wav"
                        tts = gTTS(text=text, lang="en", tld="co.in")
                        tts.save(mp3_path)
                        subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=30)
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                    # Wait for typing animation to catch up with audio
                    time.sleep(1)
                except Exception as e:
                    print(f"[{now()}] Announce all TTS error: {e}")

                announce_and_mark_read(alert)
                GLib.idle_add(self._update_counters, 1)
                time.sleep(0.5)

            GLib.idle_add(self._after_announce_all, button)'''

new_do_all = '''        def do_all():
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

content = content.replace(old_do_all, new_do_all)

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
