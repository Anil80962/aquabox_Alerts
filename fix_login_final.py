import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

# Print problematic area
print("Lines 1018-1025:")
for j in range(1017, 1025):
    if j < len(lines):
        print(f"  {j+1}: {lines[j]}")

# Fix: remove any bare USERNAME = "" / PASSWORD = "" without global
for i in range(len(lines)):
    stripped = lines[i].strip()
    if stripped == 'USERNAME = ""' or stripped == "USERNAME = ''":
        # Check if this is inside a function (indented)
        if lines[i].startswith("            "):
            lines[i] = "            pass  # handled by _set_api_creds"
            print(f"Fixed line {i+1}")
    if stripped == 'PASSWORD = ""' or stripped == "PASSWORD = ''":
        if lines[i].startswith("            "):
            lines[i] = "            pass"
            print(f"Fixed line {i+1}")

content = "\n".join(lines)

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
