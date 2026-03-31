import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add auto-announce after unread alerts are rendered
content = content.replace(
    "            # Don't auto mark - user will tap \"Mark Read\" or \"Announce\" on each alert",
    "            # Auto-announce unread alerts one by one\n"
    "            if unread_alerts:\n"
    "                threading.Thread(target=self._auto_announce_unread, args=(list(unread_alerts),), daemon=True).start()"
)

# 2. Add the method
NEW_METHOD = '''    def _auto_announce_unread(self, alerts):
        """Auto-announce unread alerts one by one."""
        import subprocess
        global _announce_stop
        _announce_stop = False
        time.sleep(3)

        for i, alert in enumerate(alerts):
            if _announce_stop:
                break
            title = alert.get("title", "")
            body = alert.get("body", "")
            desc = alert.get("description", {})
            status = desc.get("status", "")
            text = "Unread alert " + str(i+1) + " of " + str(len(alerts)) + ". " + title + ". " + body + ". " + status

            try:
                aid = alert.get("id", "")
                wav_path = _audio_cache.get(aid)
                if not wav_path or not os.path.exists(str(wav_path)):
                    from gtts import gTTS
                    mp3_path = "/tmp/auto_unread_" + str(i) + ".mp3"
                    wav_path = "/tmp/auto_unread_" + str(i) + ".wav"
                    tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)

                GLib.idle_add(self._start_typing, text)
                subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                time.sleep(1)
            except Exception as e:
                print("[" + now() + "] Auto-announce unread error: " + str(e))

            announce_and_mark_read(alert)
            time.sleep(0.5)

        print("[" + now() + "] Auto-announced " + str(len(alerts)) + " unread alerts")

'''

content = content.replace(
    "    def _on_announce_offline(self, button):",
    NEW_METHOD + "    def _on_announce_offline(self, button):"
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
