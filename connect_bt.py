import paramiko
import time
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.11', username='aquabox', password='aquabox@2026', timeout=10)

# Connect BT
bt_data = json.dumps({"mac": "2C:BE:EB:D8:B3:C0"})
cmd = f"curl -s -X POST -H 'Content-Type: application/json' -d '{bt_data}' http://localhost:8080/api/bt/connect"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
print("BT Connect:", stdout.read().decode('utf-8', errors='replace'))

time.sleep(2)

# Set audio output to bluetooth
audio_data = json.dumps({"audio_output": "bluetooth"})
cmd = f"curl -s -X POST -H 'Content-Type: application/json' -d '{audio_data}' http://localhost:8080/api/audio_output"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
print("Audio Output:", stdout.read().decode('utf-8', errors='replace'))

time.sleep(1)

# Test speak
stdin, stdout, stderr = ssh.exec_command("curl -s -X POST http://localhost:8080/api/test", timeout=5)
print("Test:", stdout.read().decode('utf-8', errors='replace'))

time.sleep(10)

# Check result
stdin, stdout, stderr = ssh.exec_command("grep 'Spoke' /home/aquabox/aquaboxtest/tts_output.log | tail -3")
print("Result:", stdout.read().decode('utf-8', errors='replace'))

ssh.close()
