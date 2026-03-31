import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.11', username='aquabox', password='aquabox@2026', timeout=10)

# Write service file using sftp to /tmp first
sftp = ssh.open_sftp()
with sftp.file('/tmp/aquabox-tts.service', 'w') as f:
    f.write("[Unit]\n")
    f.write("Description=AquaBox Text-to-Speech Service\n")
    f.write("After=network-online.target sound.target\n")
    f.write("Wants=network-online.target\n")
    f.write("\n")
    f.write("[Service]\n")
    f.write("Type=simple\n")
    f.write("User=aquabox\n")
    f.write("WorkingDirectory=/home/aquabox/aquaboxtest\n")
    f.write("ExecStart=/usr/bin/python3 /home/aquabox/aquaboxtest/tts_service.py\n")
    f.write("Restart=on-failure\n")
    f.write("RestartSec=10\n")
    f.write("Environment=PYTHONUNBUFFERED=1\n")
    f.write("\n")
    f.write("[Install]\n")
    f.write("WantedBy=multi-user.target\n")
sftp.close()

# Install service with sudo
cmd = "sudo cp /tmp/aquabox-tts.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable aquabox-tts.service"
stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
time.sleep(1)
stdin.write("aquabox@2026\n")
stdin.flush()
time.sleep(3)
out = stdout.read().decode('utf-8', errors='replace')
print(out)

# Verify
stdin2, stdout2, stderr2 = ssh.exec_command("systemctl is-enabled aquabox-tts.service 2>&1")
print("Service status:", stdout2.read().decode().strip())

ssh.close()
print("Done!")
