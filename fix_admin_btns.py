import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Add a standalone function to set API creds (not a method)
content = content.replace(
    'def precache_audio(alerts):',
    'def set_api_credentials(user, passwd, lt):\n'
    '    global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time\n'
    '    USERNAME = user\n'
    '    PASSWORD = passwd\n'
    '    LOGIN_TYPE = lt\n'
    '    token = ""\n'
    '    token_time = 0\n'
    '\n'
    'def precache_audio(alerts):'
)

# Replace all self._set_api_creds and direct global assignments with the function
content = content.replace(
    '            global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time\n'
    '            USERNAME = new_user\n'
    '            PASSWORD = new_pass\n'
    '            LOGIN_TYPE = new_lt\n'
    '            token = ""\n'
    '            token_time = 0',
    '            set_api_credentials(new_user, new_pass, new_lt)'
)

content = content.replace(
    '            global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time\n'
    '            USERNAME = api_user_entry.get_text().strip()\n'
    '            PASSWORD = api_pass_entry.get_text().strip()\n'
    '            LOGIN_TYPE = lt_combo.get_active_text()\n'
    '            token = ""\n'
    '            token_time = 0',
    '            set_api_credentials(api_user_entry.get_text().strip(), api_pass_entry.get_text().strip(), lt_combo.get_active_text())'
)

content = content.replace(
    '                        USERNAME = old_u\n'
    '                        PASSWORD = old_p\n'
    '                        LOGIN_TYPE = old_lt',
    '                        set_api_credentials(old_u, old_p, old_lt)'
)

# Also fix any remaining self._set_api_creds
content = content.replace('self._set_api_creds(', 'set_api_credentials(')

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Verify
check = 'import py_compile\ntry:\n    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)\n    print("SYNTAX OK")\nexcept py_compile.PyCompileError as e:\n    print("ERROR:", str(e))\n'
sftp2 = ssh.open_sftp()
with sftp2.file('/tmp/check.py', 'w') as f:
    f.write(check)
sftp2.close()
stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
print(stdout.read().decode('utf-8', errors='replace').strip())

ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
