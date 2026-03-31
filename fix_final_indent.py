import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

# Find error
check = 'import py_compile\ntry:\n    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)\n    print("SYNTAX OK")\nexcept py_compile.PyCompileError as e:\n    print("ERROR:", str(e))\n'
sftp = ssh.open_sftp()
with sftp.file('/tmp/check.py', 'w') as f:
    f.write(check)

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
result = stdout.read().decode('utf-8', errors='replace').strip()
print(result)

if 'ERROR' in result:
    import re
    m = re.search(r'line (\d+)', result)
    if m:
        line_num = int(m.group(1))

        lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

        # Show context
        for j in range(max(0, line_num-3), min(len(lines), line_num+3)):
            print(f"  {j+1}: [{lines[j]}]")

        # Fix: replace all broken TTS lines with clean version
        content = '\n'.join(lines)

        # Replace all the messy TTS conditional with a clean helper
        # First remove all broken tts lines
        content = content.replace(
            'tts_tld = "co.in" if TTS_LANG == "en" else None\n                    tts = gTTS(text=text, lang=TTS_LANG, tld=tts_tld) if tts_tld else gTTS(text=text, lang=TTS_LANG)',
            'tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")'
        )

        with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
            f.write(content)

        # Check again
        stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
        result2 = stdout.read().decode('utf-8', errors='replace').strip()
        print("After fix:", result2)

        if 'ERROR' in result2:
            # Still broken - find and show
            m2 = re.search(r'line (\d+)', result2)
            if m2:
                ln = int(m2.group(1))
                lines2 = content.split('\n')
                for j in range(max(0, ln-3), min(len(lines2), ln+3)):
                    indent = len(lines2[j]) - len(lines2[j].lstrip())
                    print(f"  {j+1} (i={indent}): [{lines2[j]}]")

                # Try to fix by aligning with surrounding code
                bad_line = lines2[ln-1]
                bad_indent = len(bad_line) - len(bad_line.lstrip())
                # Check prev line indent
                prev_indent = len(lines2[ln-2]) - len(lines2[ln-2].lstrip())
                if bad_indent != prev_indent:
                    lines2[ln-1] = ' ' * prev_indent + bad_line.lstrip()
                    content = '\n'.join(lines2)
                    with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
                        f.write(content)

                    stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
                    print("After fix2:", stdout.read().decode('utf-8', errors='replace').strip())

sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
ssh.exec_command('killall aplay 2>/dev/null')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
