import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Fix on_login - user must enter the SAME credentials that admin configured
# Find on_login method and replace the logic
old_on_login = '''    def on_login(self, widget):
        global USERNAME, PASSWORD, LOGGED_IN, LOGIN_TYPE
        u = self.username_entry.get_text().strip()
        p = self.password_entry.get_text().strip()
        if not u or not p:
            self.error_label.set_text("Enter username and password")
            return
        USERNAME = u
        PASSWORD = p
        self.error_label.set_text("Logging in...")
        def try_login():
            success = get_token()
            GLib.idle_add(self._login_result, success)
        threading.Thread(target=try_login, daemon=True).start()'''

new_on_login = '''    def on_login(self, widget):
        global USERNAME, PASSWORD, LOGGED_IN, LOGIN_TYPE
        u = self.username_entry.get_text().strip()
        p = self.password_entry.get_text().strip()
        if not u or not p:
            self.error_label.set_text("Enter username and password")
            return

        # Check if admin has configured API credentials
        if os.path.exists(ADMIN_CONFIG):
            try:
                with open(ADMIN_CONFIG) as f:
                    cfg = json.load(f)
                saved_user = cfg.get("api_username", "")
                saved_pass = cfg.get("api_password", "")
                if saved_user and saved_pass:
                    # User must enter the same credentials admin set
                    if u != saved_user or p != saved_pass:
                        self.error_label.set_text("Invalid credentials")
                        return
            except:
                pass

        USERNAME = u
        PASSWORD = p
        self.error_label.set_text("Logging in...")
        def try_login():
            success = get_token()
            GLib.idle_add(self._login_result, success)
        threading.Thread(target=try_login, daemon=True).start()'''

content = content.replace(old_on_login, new_on_login)

# 2. Fix _login_result - don't save admin config on normal login
content = content.replace(
    '            save_admin_config(USERNAME, PASSWORD, LOGIN_TYPE)',
    '            # Admin config already set by admin page'
)

# 3. Remove "Admin Settings" button from login page
# Admin should have a separate entry - just admin username/password fields
# Replace the admin button with a cleaner approach
content = content.replace(
    "        # Admin settings button\n"
    "        admin_btn = Gtk.Button(label=\"\\u2699  Admin Settings\")\n"
    "        admin_btn.modify_font(Pango.FontDescription(\"Sans 9\"))\n"
    "        admin_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 0.7))\n"
    "        admin_btn.set_margin_start(30)\n"
    "        admin_btn.set_margin_end(30)\n"
    "        admin_btn.set_margin_bottom(15)\n"
    "        admin_btn.connect(\"clicked\", self._open_admin)\n"
    "        box.pack_start(admin_btn, False, False, 0)",

    "        # Admin settings button\n"
    "        admin_btn = Gtk.Button(label=\"\\u2699  Admin\")\n"
    "        admin_btn.modify_font(Pango.FontDescription(\"Sans 8\"))\n"
    "        admin_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.5, 0.5, 0.6, 0.5))\n"
    "        admin_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))\n"
    "        admin_btn.set_margin_start(30)\n"
    "        admin_btn.set_margin_end(30)\n"
    "        admin_btn.set_margin_bottom(10)\n"
    "        admin_btn.connect(\"clicked\", self._open_admin)\n"
    "        box.pack_start(admin_btn, False, False, 0)"
)

# 4. Show message on login page if no admin config exists
content = content.replace(
    "        self.error_label = Gtk.Label(label=\"\")",
    "        # Check if admin configured credentials\n"
    "        if not os.path.exists(ADMIN_CONFIG):\n"
    "            self.error_label = Gtk.Label(label=\"Admin setup required first\")\n"
    "            self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.5, 0.1, 1))\n"
    "        else:\n"
    "            self.error_label = Gtk.Label(label=\"\")"
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Delete old session and config to start fresh
ssh.exec_command('rm -f /home/aquabox/Desktop/Aquabox/user_session.json')
ssh.exec_command('rm -f /home/aquabox/Desktop/Aquabox/admin_config.json')

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command('journalctl -u aquabox-alerts.service --no-pager -n 3 2>&1 | grep -i error | grep -v AT-SPI | grep -v Deprecation')
err = stdout.read().decode('utf-8', errors='replace').strip()
print('Errors:', err if err else 'None')

ssh.close()
print('Done!')
