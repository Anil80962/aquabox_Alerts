import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Find _add_bot_message and check if speak param exists
idx = content.find('def _add_bot_message(self, text, speak=False):')
if idx == -1:
    idx = content.find('def _add_bot_message(self, text):')
    if idx != -1:
        content = content.replace(
            'def _add_bot_message(self, text):',
            'def _add_bot_message(self, text, speak=False):'
        )
        print("Added speak parameter")

# Find the typing tick setup and add speak after it
# Search for the timeout_add line for typing
tick_line = 'GLib.timeout_add(25, self._chat_typing_tick)'
if tick_line in content:
    # Check if speak code already follows
    tick_idx = content.find(tick_line)
    after = content[tick_idx:tick_idx+300]
    if '_speak_bot_answer' not in after and 'speak' not in after:
        content = content.replace(
            tick_line,
            tick_line + '\n\n'
            '        # Speak the answer through speaker\n'
            '        if speak and text:\n'
            '            def do_speak():\n'
            '                try:\n'
            '                    import subprocess\n'
            '                    from gtts import gTTS\n'
            '                    if TTS_LANG != "en":\n'
            '                        tts = gTTS(text=text, lang=TTS_LANG)\n'
            '                    else:\n'
            '                        tts = gTTS(text=text, lang="en", tld="co.in")\n'
            '                    tts.save("/tmp/aquabox_chat.mp3")\n'
            '                    subprocess.run(["ffmpeg", "-y", "-i", "/tmp/aquabox_chat.mp3", "-ar", "44100", "/tmp/aquabox_chat.wav"], capture_output=True, timeout=15)\n'
            '                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", "/tmp/aquabox_chat.wav"], capture_output=True, timeout=30)\n'
            '                except Exception as e:\n'
            '                    print("[AquaBox Chat] Speak error: " + str(e))\n'
            '            threading.Thread(target=do_speak, daemon=True).start()'
        )
        print("Added speak code after typing tick")
    else:
        print("Speak code already exists")
else:
    print("Could not find typing tick line")

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Verify
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
