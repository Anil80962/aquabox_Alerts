import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Replace the play section to start typing first, then play audio in parallel
old_play = '''            # Step 2: Play each one sequentially - typing + audio together, wait for finish
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
                time.sleep(1)'''

new_play = '''            # Step 2: Play each one - start typing, then immediately start audio
            GLib.idle_add(button.set_label, "Playing alerts...")
            for i, alert in enumerate(alerts):
                if _announce_stop:
                    break
                if i >= len(audio_files) or not audio_files[i]:
                    continue

                # Start typing animation
                GLib.idle_add(self._start_typing, texts[i])
                time.sleep(0.1)  # Tiny wait for typing to render

                # Start audio in a subprocess (non-blocking)
                audio_proc = subprocess.Popen(["aplay", "-D", "plughw:2,0", "-q", audio_files[i]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Wait for audio to finish completely
                audio_proc.wait()

                # Audio done - mark as read
                if not _announce_stop:
                    announce_and_mark_read(alert)
                    GLib.idle_add(self._update_counters, 1)

                # Pause between alerts
                time.sleep(0.5)'''

content = content.replace(old_play, new_play)

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
