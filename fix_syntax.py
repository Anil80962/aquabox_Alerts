import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

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
        ln = int(m.group(1))
        lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')
        for j in range(max(0, ln-5), min(len(lines), ln+5)):
            print(f"  {j+1}: [{lines[j]}]")

sftp.close()
ssh.close()
