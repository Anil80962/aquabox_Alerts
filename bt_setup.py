import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.11', username='aquabox', password='aquabox@2026', timeout=10)

# Write a shell script to the Pi that handles bluetooth setup
bt_script = """#!/bin/bash
echo "=== Unblocking Bluetooth ==="
sudo rfkill unblock bluetooth
sleep 2

echo "=== Powering ON Bluetooth ==="
bluetoothctl power on
sleep 2

echo "=== Bluetooth Status ==="
bluetoothctl show | grep -E "Powered|Name|Alias"

echo "=== Setting Agent ==="
bluetoothctl agent on
bluetoothctl default-agent

echo "=== Scanning for 12 seconds ==="
timeout 12 bluetoothctl --timeout 12 scan on 2>&1 || true
sleep 1

echo "=== Discovered Devices ==="
bluetoothctl devices
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/bt_setup.sh', 'w') as f:
    f.write(bt_script)
sftp.close()

# Run it with sudo password via pty
stdin, stdout, stderr = ssh.exec_command(
    'echo "aquabox@2026" | sudo -S bash /tmp/bt_setup.sh 2>&1',
    timeout=30
)

# Wait and read output
time.sleep(20)
out = stdout.read().decode('utf-8', errors='replace')
print(out)

ssh.close()
print("\nDone! Check the device list above.")
