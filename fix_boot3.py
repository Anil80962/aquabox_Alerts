import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=15)

# 1. Remove Plymouth completely - it causes the blue lines
cmds = [
    'echo "aquabox@2026" | sudo -S apt-get remove -y plymouth plymouth-themes plymouth-label 2>&1 | tail -3',
    'echo "aquabox@2026" | sudo -S apt-get autoremove -y 2>&1 | tail -3',
]

for cmd in cmds:
    print('Running:', cmd[:60])
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    time.sleep(10)
    print(stdout.read().decode('utf-8', errors='replace').strip())

# 2. Remove splash from cmdline since plymouth is gone
sftp = ssh.open_sftp()
cmdline = sftp.file('/boot/firmware/cmdline.txt', 'r').read().decode().strip()
cmdline = cmdline.replace(' splash', '')
cmdline = cmdline.replace(' plymouth.ignore-serial-consoles', '')
with sftp.file('/tmp/cmdline.txt', 'w') as f:
    f.write(cmdline)
sftp.close()
ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/cmdline.txt /boot/firmware/cmdline.txt')
time.sleep(1)
print('Removed plymouth from cmdline')

# 3. Make the boot splash service start FIRST and cover the entire boot
# It will show the water animation from power-on until alerts app takes over
BOOT_SERVICE = '''[Unit]
Description=AquaBox Boot Splash
DefaultDependencies=no
After=systemd-user-sessions.service
Before=graphical.target aquabox-alerts.service

[Service]
Type=simple
User=aquabox
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=GDK_BACKEND=wayland
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
ExecStart=/usr/bin/python3 /home/aquabox/Desktop/Aquabox/boot_splash.py
Restart=on-failure
RestartSec=2
TimeoutStopSec=5

[Install]
WantedBy=graphical.target
'''

sftp2 = ssh.open_sftp()
with sftp2.file('/tmp/aquabox-bootsplash.service', 'w') as f:
    f.write(BOOT_SERVICE)
sftp2.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/aquabox-bootsplash.service /etc/systemd/system/')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl daemon-reload')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl enable aquabox-bootsplash.service')
time.sleep(1)

# 4. Make tty1 show black screen with no text at all
ssh.exec_command('echo "aquabox@2026" | sudo -S bash -c "mkdir -p /etc/systemd/system/getty@tty1.service.d"')
time.sleep(0.5)

TTY_OVERRIDE = '''[Service]
ExecStart=
ExecStart=-/sbin/agetty --skip-login --noclear --noissue --login-options "-f root" %I linux
StandardInput=tty
StandardOutput=null
'''
sftp3 = ssh.open_sftp()
with sftp3.file('/tmp/tty-override.conf', 'w') as f:
    f.write(TTY_OVERRIDE)
sftp3.close()

# Actually just mask tty1 completely
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl mask getty@tty1.service')
time.sleep(1)

# 5. Clear /etc/issue and /etc/motd to remove any text
ssh.exec_command('echo "aquabox@2026" | sudo -S bash -c "echo > /etc/issue"')
ssh.exec_command('echo "aquabox@2026" | sudo -S bash -c "echo > /etc/motd"')

# 6. Set framebuffer console to black with no cursor
# Create a script that runs very early to blank the screen
BLANK_SCRIPT = '''#!/bin/bash
# Blank the console immediately
setterm --blank force --cursor off > /dev/tty1 2>/dev/null
echo -e "\\033[9;0]" > /dev/tty1 2>/dev/null
echo -e "\\033[?25l" > /dev/tty1 2>/dev/null
# Set console colors to black on black
echo -e "\\033[40m\\033[30m\\033[2J" > /dev/tty1 2>/dev/null
'''

sftp4 = ssh.open_sftp()
with sftp4.file('/tmp/blank-console.sh', 'w') as f:
    f.write(BLANK_SCRIPT)
sftp4.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/blank-console.sh /usr/local/bin/blank-console.sh')
ssh.exec_command('echo "aquabox@2026" | sudo -S chmod +x /usr/local/bin/blank-console.sh')

# Create systemd service for blanking console very early
BLANK_SERVICE = '''[Unit]
Description=Blank Console
DefaultDependencies=no
After=sysinit.target
Before=basic.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/blank-console.sh
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
'''

sftp5 = ssh.open_sftp()
with sftp5.file('/tmp/blank-console.service', 'w') as f:
    f.write(BLANK_SERVICE)
sftp5.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/blank-console.service /etc/systemd/system/')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl daemon-reload')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl enable blank-console.service')
time.sleep(1)

print('All done. Rebooting...')
ssh.exec_command('echo "aquabox@2026" | sudo -S reboot')
ssh.close()
