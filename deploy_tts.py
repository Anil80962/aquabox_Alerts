import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.11', username='aquabox', password='aquabox@2026', timeout=10)

# Force kill existing service
print("Force killing existing TTS service...")
stdin, stdout, stderr = ssh.exec_command('pkill -9 -f tts_service.py 2>/dev/null')
stdout.read()
time.sleep(2)

# Verify killed
stdin, stdout, stderr = ssh.exec_command('pgrep -f tts_service || echo "Process killed"')
print(stdout.read().decode('utf-8', errors='replace').strip())

# Transfer updated file
print("Uploading updated tts_service.py...")
sftp = ssh.open_sftp()
sftp.put(
    r'C:\Users\Anil Fluxgen\Downloads\ZEST_MEATER_CODE\ZEST_MEATER_CODE\tts_service.py',
    '/home/aquabox/aquaboxtest/tts_service.py'
)
sftp.close()

# Start the service with proper env
print("Starting TTS service...")
stdin, stdout, stderr = ssh.exec_command(
    'cd /home/aquabox/aquaboxtest && XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus nohup python3 tts_service.py > tts_output.log 2>&1 &'
)
stdout.read()

# Don't wait too long - just check after a few seconds
time.sleep(5)

# Check if running
stdin, stdout, stderr = ssh.exec_command('pgrep -f tts_service && echo "RUNNING" || echo "NOT RUNNING"')
print(stdout.read().decode('utf-8', errors='replace').strip())

# Show log
stdin, stdout, stderr = ssh.exec_command('head -20 /home/aquabox/aquaboxtest/tts_output.log')
print("=== Log ===")
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Deploy complete!")
