#!/usr/bin/env python3
"""
Deploy WiFi Manager to Raspberry Pi.
Usage: python deploy_wifi_manager.py <pi_ip>
"""

import paramiko
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PI_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.11"
PI_USER = "aquabox"
PI_PASS = "aquabox@2026"
REMOTE_DIR = "/home/aquabox/aquaboxtest"

print(f"Connecting to {PI_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(PI_IP, username=PI_USER, password=PI_PASS, timeout=10)
print("Connected!")

# Upload wifi_manager.py
print("Uploading wifi_manager.py...")
sftp = ssh.open_sftp()
sftp.put("wifi_manager.py", f"{REMOTE_DIR}/wifi_manager.py")
sftp.close()

# Make executable
ssh.exec_command(f"chmod +x {REMOTE_DIR}/wifi_manager.py")
time.sleep(1)

# Create systemd service
print("Installing systemd service...")
service = f"""[Unit]
Description=AquaBox WiFi Manager
After=network.target NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
User=root
WorkingDirectory={REMOTE_DIR}
ExecStart=/usr/bin/python3 {REMOTE_DIR}/wifi_manager.py
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/aquabox-wifi.service', 'w') as f:
    f.write(service)
sftp.close()

# Install service with sudo
stdin, stdout, stderr = ssh.exec_command(
    'echo "aquabox@2026" | sudo -S bash -c "'
    'cp /tmp/aquabox-wifi.service /etc/systemd/system/ && '
    'systemctl daemon-reload && '
    'systemctl enable aquabox-wifi.service && '
    'systemctl restart aquabox-wifi.service'
    '"',
    timeout=15
)
time.sleep(5)
print(stdout.read().decode('utf-8', errors='replace'))

# Verify
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-wifi.service')
status = stdout.read().decode().strip()
print(f"Service status: {status}")

stdin, stdout, stderr = ssh.exec_command(f'curl -s http://localhost:8090/api/status 2>/dev/null || curl -s http://localhost:80/api/status 2>/dev/null')
print(f"API: {stdout.read().decode('utf-8', errors='replace')[:200]}")

ssh.close()
print("\nDeploy complete!")
print(f"If Pi is on WiFi: http://{PI_IP}:8090")
print(f"If Pi is in AP mode: Connect to 'AquaBox-Setup' (password: aquabox123), then open http://192.168.4.1")
