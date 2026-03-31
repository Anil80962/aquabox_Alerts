import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()

# 1. Fix config.txt - move disable_splash before [all], add avoid_warnings
config = sftp.file('/boot/firmware/config.txt', 'r').read().decode()

# Remove old disable_splash from wrong place
config = config.replace('\ndisable_splash=1', '')

# Add proper boot display settings before [all]
if 'disable_splash=1' not in config:
    config = config.replace(
        '[all]\nenable_uart=1',
        '# Clean boot - no rainbow, no warnings\n'
        'disable_splash=1\n'
        'avoid_warnings=1\n'
        'boot_delay=0\n'
        '\n[all]\nenable_uart=1'
    )

with sftp.file('/tmp/config.txt', 'w') as f:
    f.write(config)
sftp.close()
ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/config.txt /boot/firmware/config.txt')
time.sleep(1)
print('config.txt fixed')

# 2. Fix cmdline - completely clean
new_cmdline = (
    'console=serial0,115200 console=tty3 '
    'root=PARTUUID=c6cbd837-02 rootfstype=ext4 fsck.repair=yes rootwait '
    'quiet splash loglevel=0 '
    'plymouth.ignore-serial-consoles '
    'vt.global_cursor_default=0 logo.nologo '
    'cfg80211.ieee80211_regdom=IN '
    'systemd.show_status=0 rd.udev.log_level=0'
)

sftp2 = ssh.open_sftp()
with sftp2.file('/tmp/cmdline.txt', 'w') as f:
    f.write(new_cmdline)
sftp2.close()
ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/cmdline.txt /boot/firmware/cmdline.txt')
time.sleep(1)
print('cmdline fixed')

# 3. Set Plymouth theme and rebuild
stdin, stdout, stderr = ssh.exec_command(
    'echo "aquabox@2026" | sudo -S /usr/sbin/plymouth-set-default-theme -R aquabox 2>&1',
    timeout=120
)
time.sleep(30)
out = stdout.read().decode('utf-8', errors='replace')
print('Plymouth:', out[-100:] if out else 'done')

# 4. Disable getty on tty1 (the blue text console)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl disable getty@tty1.service 2>/dev/null')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl mask getty@tty1.service 2>/dev/null')
time.sleep(1)
print('Disabled tty1 console')

# 5. Set black background for virtual console (before X/Wayland starts)
ssh.exec_command('echo "aquabox@2026" | sudo -S bash -c "echo -e \\\"\\\\033[9;0]\\\" > /etc/issue"')
time.sleep(1)

# 6. Hide cursor on framebuffer console
ssh.exec_command('echo "aquabox@2026" | sudo -S bash -c "setterm --cursor off > /dev/tty1 2>/dev/null"')

print('All fixes applied. Rebooting...')
ssh.exec_command('echo "aquabox@2026" | sudo -S reboot')
ssh.close()
