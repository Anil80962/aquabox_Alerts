import paramiko
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.11', username='aquabox', password='aquabox@2026', timeout=10)

cmds = [
    'XDG_RUNTIME_DIR=/run/user/1000 wpctl status 2>&1 | head -40',
    'aplay -L 2>&1 | grep -i -A1 blue',
    # Test default aplay with XDG set
    'espeak-ng -v en -s 150 -a 90 --stdout "hello bluetooth test" | XDG_RUNTIME_DIR=/run/user/1000 aplay -q 2>&1; echo "EXIT=$?"',
    # Test pw-play
    'which pw-play 2>&1',
    'espeak-ng -v en -s 150 -a 90 --stdout "pw play test" | XDG_RUNTIME_DIR=/run/user/1000 pw-play --target 0 - 2>&1; echo "EXIT=$?"',
    # Check if pipewire-pulse is installed
    'dpkg -l | grep pipewire-pulse 2>&1',
    'apt list --installed 2>/dev/null | grep -i pulseaudio-utils',
    # Install pactl if needed
    'sudo apt-get install -y pulseaudio-utils 2>&1 | tail -3',
]

for cmd in cmds:
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15, get_pty='sudo' in cmd)
    if 'sudo' in cmd:
        import time
        time.sleep(0.5)
        stdin.write('aquabox@2026\n')
        stdin.flush()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip(): print(out.strip())
    if err.strip(): print('ERR:', err.strip())
    print()

ssh.close()
