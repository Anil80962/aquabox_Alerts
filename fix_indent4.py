import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

# Remove ALL "if _announce_stop: break" lines that are NOT inside a for loop
# Check by looking backwards for the nearest "for" statement
fixes = 0
for i in range(len(lines)):
    if 'if _announce_stop: break' in lines[i].strip():
        # Look backwards to find if we're inside a for loop
        indent = len(lines[i]) - len(lines[i].lstrip())
        in_for = False
        for j in range(i-1, max(0, i-30), -1):
            stripped = lines[j].lstrip()
            line_indent = len(lines[j]) - len(stripped)
            if line_indent < indent and stripped.startswith('for '):
                in_for = True
                break
            if line_indent < indent and (stripped.startswith('def ') or stripped.startswith('class ')):
                break

        if not in_for:
            # Replace with a simple if/return or just comment out
            lines[i] = lines[i].replace('if _announce_stop: break', 'if _announce_stop: pass  # cancelled')
            fixes += 1
            print(f"Fixed line {i+1}: break outside loop -> pass")

print(f"Total fixes: {fixes}")

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
print(result)

if 'SYNTAX OK' in result:
    ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
    time.sleep(2)
    ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
    time.sleep(4)
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
    print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
else:
    print("Still has errors - need manual fix")

ssh.close()
print('Done!')
