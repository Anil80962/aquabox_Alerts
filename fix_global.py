import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Fix all the global declaration issues in nested functions
# Replace "global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time" in on_save
content = content.replace(
    "        def on_save(btn):\n            global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time",
    "        def on_save(btn):"
)

# Replace "global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time" in on_test
content = content.replace(
    "        def on_test(btn):\n            global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time",
    "        def on_test(btn):"
)

# Fix inner global in on_test result handler
content = content.replace(
    "                        global USERNAME, PASSWORD, LOGIN_TYPE\n                        USERNAME, PASSWORD, LOGIN_TYPE = old_u, old_p, old_lt",
    "                        pass"
)

# Now add _set_api_creds method if not already there
if '_set_api_creds' not in content:
    content = content.replace(
        "    def _show_admin_settings(self):",
        "    def _set_api_creds(self, user, passwd, lt):\n"
        "        global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time\n"
        "        USERNAME = user\n"
        "        PASSWORD = passwd\n"
        "        LOGIN_TYPE = lt\n"
        "        token = \"\"\n"
        "        token_time = 0\n"
        "\n"
        "    def _show_admin_settings(self):"
    )

# Replace direct variable assignments in on_save with _set_api_creds call
content = content.replace(
    "            USERNAME = new_user\n            PASSWORD = new_pass\n            LOGIN_TYPE = new_lt\n            token = \"\"\n            token_time = 0",
    "            self._set_api_creds(new_user, new_pass, new_lt)"
)

# Replace direct variable assignments in on_test
content = content.replace(
    "            old_u, old_p, old_lt = USERNAME, PASSWORD, LOGIN_TYPE\n            USERNAME = api_user_entry.get_text().strip()\n            PASSWORD = api_pass_entry.get_text().strip()\n            LOGIN_TYPE = lt_combo.get_active_text()\n            token = \"\"\n            token_time = 0",
    "            old_u, old_p, old_lt = USERNAME, PASSWORD, LOGIN_TYPE\n            self._set_api_creds(api_user_entry.get_text().strip(), api_pass_entry.get_text().strip(), lt_combo.get_active_text())"
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command('journalctl -u aquabox-alerts.service --no-pager -n 5 2>&1 | grep -i error | grep -v AT-SPI | grep -v Deprecation | head -3')
err = stdout.read().decode('utf-8', errors='replace').strip()
print('Errors:', err if err else 'None')

ssh.close()
print('Done!')
