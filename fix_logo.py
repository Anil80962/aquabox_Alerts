import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/logo/display_logo.py', 'r').read().decode()

# 1. Change interval to 5 minutes
content = content.replace(
    'DISPLAY_INTERVAL = 60   # seconds between shows',
    'DISPLAY_INTERVAL = 300  # 5 minutes between shows'
)

# 2. Add aplay check before showing logo
old_idle = '        if is_idle():\n            print("Showing logo animation...")\n            show_logo()'

new_idle = (
    '        if is_idle():\n'
    '            # Skip if announce/TTS is playing\n'
    '            import subprocess as _sp\n'
    '            _chk = _sp.run(["pgrep", "-f", "aplay"], capture_output=True)\n'
    '            if _chk.returncode == 0:\n'
    '                print("Audio playing, skipping animation")\n'
    '                time.sleep(10)\n'
    '                continue\n'
    '            print("Showing logo animation...")\n'
    '            show_logo()'
)

content = content.replace(old_idle, new_idle)

with sftp.file('/home/aquabox/Desktop/logo/display_logo.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl restart fluxgen-logo.service')
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active fluxgen-logo.service')
print('Logo service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
