import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.11', username='aquabox', password='aquabox@2026', timeout=10)

# Scan again for Fluxgen_2
scan_script = """#!/bin/bash
echo "=== Scanning for 15 seconds ==="
timeout 15 bluetoothctl --timeout 15 scan on 2>&1 || true
sleep 1

echo "=== All Discovered Devices ==="
bluetoothctl devices

echo "=== Looking for Fluxgen_2 ==="
bluetoothctl devices | grep -i fluxgen || echo "Fluxgen_2 NOT found yet"
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/bt_scan.sh', 'w') as f:
    f.write(scan_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('bash /tmp/bt_scan.sh 2>&1', timeout=30)
time.sleep(20)
out = stdout.read().decode('utf-8', errors='replace')
print(out)

ssh.close()
