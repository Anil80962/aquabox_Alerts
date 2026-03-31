import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add OFFLINE_ANNOUNCE_INTERVAL config if missing
if 'OFFLINE_ANNOUNCE_INTERVAL' not in content:
    content = content.replace(
        'REFRESH_INTERVAL = 120',
        'REFRESH_INTERVAL = 120  # seconds (2 minutes)\nOFFLINE_ANNOUNCE_INTERVAL = 3600  # 1 hour auto-announce offline'
    )

# 2. Add timer in AlertsWindow __init__
content = content.replace(
    '        GLib.timeout_add_seconds(REFRESH_INTERVAL, self.refresh_alerts)',
    '        GLib.timeout_add_seconds(REFRESH_INTERVAL, self.refresh_alerts)\n'
    '        GLib.timeout_add_seconds(3600, self._auto_announce_offline_timer)'
)

# 3. Add the auto-announce offline timer method
NEW_METHOD = '''    def _auto_announce_offline_timer(self):
        """Auto-announce offline alerts every 1 hour."""
        if not self._all_offline_alerts:
            return True
        print("[" + now() + "] Auto-announcing " + str(len(self._all_offline_alerts)) + " offline alerts (hourly)")

        def do_offline_auto():
            import subprocess
            global _announce_stop
            _announce_stop = False
            alerts = list(self._all_offline_alerts)

            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                title = alert.get("title", "")
                desc = alert.get("description", {})
                status = desc.get("status", "")
                text = "Offline unit " + str(i+1) + " of " + str(len(alerts)) + ". " + title + ". " + status

                try:
                    from gtts import gTTS
                    mp3_path = "/tmp/auto_offline_" + str(i) + ".mp3"
                    wav_path = "/tmp/auto_offline_" + str(i) + ".wav"
                    tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save(mp3_path)
                    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", wav_path], capture_output=True, timeout=15)
                    GLib.idle_add(self._start_typing, text)
                    subprocess.run(["aplay", "-D", "plughw:2,0", "-q", wav_path], capture_output=True, timeout=30)
                    time.sleep(1)
                except Exception as e:
                    print("[" + now() + "] Auto offline announce error: " + str(e))
                time.sleep(0.5)

        threading.Thread(target=do_offline_auto, daemon=True).start()
        return True  # Keep timer running

'''

content = content.replace(
    '    def _on_announce_offline(self, button):',
    NEW_METHOD + '    def _on_announce_offline(self, button):'
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

# Verify
stdin, stdout, stderr = ssh.exec_command('grep -n "_auto_announce_offline_timer" /home/aquabox/Desktop/Aquabox/aquabox_alerts.py | head -3')
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print('Done!')
