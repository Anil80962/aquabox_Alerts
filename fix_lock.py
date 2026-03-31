import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Remove the _announcing lock completely - it causes more problems than it solves
# Just use _announce_stop flag and killall aplay

# Remove _announcing variable
content = content.replace(
    "_announcing = False  # Only one announce at a time",
    "# No lock needed - _announce_stop handles cancellation"
)

# Remove _start_announcing function - replace with simple stop+reset
content = content.replace(
    "def _start_announcing():\n"
    "    global _announcing, _announce_stop\n"
    "    if _announcing:\n"
    "        # Stop current announce first\n"
    "        _announce_stop = True\n"
    "        import subprocess\n"
    "        subprocess.run([\"killall\", \"aplay\"], capture_output=True)\n"
    "        import time\n"
    "        time.sleep(0.5)\n"
    "    _announce_stop = False\n"
    "    _announcing = True\n"
    "    return True",
    "def _start_announcing():\n"
    "    global _announce_stop\n"
    "    _announce_stop = True\n"
    "    import subprocess\n"
    "    subprocess.run([\"killall\", \"aplay\"], capture_output=True)\n"
    "    import time\n"
    "    time.sleep(0.3)\n"
    "    _announce_stop = False\n"
    "    return True"
)

# Remove _stop_announcing function - replace with simple pass
content = content.replace(
    "def _stop_announcing():\n"
    "    global _announcing\n"
    "    _announcing = False",
    "def _stop_announcing():\n"
    "    pass  # No lock to release"
)

# Fix _cancel_announce - remove _announcing reference
content = content.replace(
    "        global _announce_stop, _announcing\n"
    "        _announce_stop = True\n"
    "        _announcing = False",
    "        global _announce_stop\n"
    "        _announce_stop = True"
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Verify syntax
check = 'import py_compile\ntry:\n    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)\n    print("SYNTAX OK")\nexcept py_compile.PyCompileError as e:\n    print("ERROR:", str(e))\n'
sftp2 = ssh.open_sftp()
with sftp2.file('/tmp/check.py', 'w') as f:
    f.write(check)
sftp2.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
print(stdout.read().decode('utf-8', errors='replace').strip())

ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
ssh.exec_command('killall aplay 2>/dev/null')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
