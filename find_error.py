import paramiko, sys, io, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()

# Write a check script
check = 'import py_compile\ntry:\n    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)\n    print("OK")\nexcept py_compile.PyCompileError as e:\n    print(str(e))\n'
with sftp.file('/tmp/check_syntax.py', 'w') as f:
    f.write(check)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check_syntax.py 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

# Also fix credentials to working ones
sftp2 = ssh.open_sftp()
with sftp2.file('/home/aquabox/Desktop/Aquabox/admin_config.json', 'w') as f:
    f.write(json.dumps({"api_username": "sartorius", "api_password": "sartorius@1234", "login_type": "DEFAULT"}))
with sftp2.file('/home/aquabox/Desktop/Aquabox/user_session.json', 'w') as f:
    f.write(json.dumps({"username": "sartorius", "password": "sartorius@1234"}))
sftp2.close()
print("Credentials fixed to sartorius")

ssh.close()
