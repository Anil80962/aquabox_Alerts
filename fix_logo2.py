import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/logo/display_logo.py', 'r').read().decode()

# 1. Increase idle threshold to 5 minutes (user must be idle for 5 min)
content = content.replace(
    'IDLE_THRESHOLD = 30  # seconds of no input before showing logo',
    'IDLE_THRESHOLD = 300  # 5 minutes of no input before showing logo'
)

# 2. Also check if aquabox_alerts overlay/announce is active
old_check = (
    '            # Skip if announce/TTS is playing\n'
    '            import subprocess as _sp\n'
    '            _chk = _sp.run(["pgrep", "-f", "aplay"], capture_output=True)\n'
    '            if _chk.returncode == 0:\n'
    '                print("Audio playing, skipping animation")\n'
    '                time.sleep(10)\n'
    '                continue'
)

new_check = (
    '            # Skip if announce/TTS is playing or user recently active\n'
    '            import subprocess as _sp\n'
    '            _chk1 = _sp.run(["pgrep", "-f", "aplay"], capture_output=True)\n'
    '            _chk2 = _sp.run(["pgrep", "-f", "wvkbd"], capture_output=True)\n'
    '            if _chk1.returncode == 0 or _chk2.returncode == 0:\n'
    '                print("Audio/keyboard active, skipping animation")\n'
    '                time.sleep(10)\n'
    '                continue'
)

content = content.replace(old_check, new_check)

with sftp.file('/home/aquabox/Desktop/logo/display_logo.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl restart fluxgen-logo.service')
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active fluxgen-logo.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
