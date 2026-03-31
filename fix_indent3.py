import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

# Print all problem areas - lines with "if _announce_stop: break" + next 4 lines
for i in range(len(lines)):
    if 'if _announce_stop: break' in lines[i]:
        print(f"\n--- Block at line {i+1} ---")
        for j in range(i, min(i+6, len(lines))):
            indent = len(lines[j]) - len(lines[j].lstrip())
            print(f"  {j+1} (indent={indent}): [{lines[j]}]")

        # The pattern is:
        # if _announce_stop: break     (indent X+4)
        # tts = gTTS(...)              (indent X)    <- should be X+4
        # tts.save(...)                (indent X+4)  <- correct
        # subprocess.run(ffmpeg...)    (indent X+4)  <- correct

        # Fix: make all these lines same indent as the "if" line
        if_indent = len(lines[i]) - len(lines[i].lstrip())
        for j in range(i+1, min(i+4, len(lines))):
            stripped = lines[j].lstrip()
            if stripped and any(kw in stripped for kw in ['tts =', 'tts.save', 'subprocess.run']):
                cur_indent = len(lines[j]) - len(stripped)
                if cur_indent != if_indent:
                    lines[j] = ' ' * if_indent + stripped
                    print(f"  FIXED line {j+1} indent {cur_indent} -> {if_indent}")

content = '\n'.join(lines)
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
result = stdout.read().decode('utf-8', errors='replace').strip()
print("\n" + result)

if 'SYNTAX OK' in result:
    ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
    time.sleep(2)
    ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
    time.sleep(4)
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
    print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
