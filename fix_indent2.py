import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

# Find ALL lines with "if _announce_stop: break" and fix surrounding indentation
fixes = 0
for i in range(len(lines)):
    if 'if _announce_stop: break' in lines[i]:
        indent = len(lines[i]) - len(lines[i].lstrip())
        spaces = ' ' * indent

        # Fix next lines that should be at same indent but are indented more
        for j in range(i+1, min(i+5, len(lines))):
            next_line = lines[j].lstrip()
            next_indent = len(lines[j]) - len(next_line)
            # If indented more than the if line, and it's a code line
            if next_indent > indent and next_line and not next_line.startswith('#'):
                # Check if it's tts/subprocess/save that should be at same level
                if any(kw in next_line for kw in ['tts =', 'tts.save', 'subprocess.run']):
                    lines[j] = spaces + next_line
                    fixes += 1
                    print(f"Fixed line {j+1}: {next_line[:50]}")

print(f"Total fixes: {fixes}")

content = '\n'.join(lines)
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

# Restart
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
