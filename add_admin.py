import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add admin config file path and functions after CREDS_FILE
content = content.replace(
    "CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"user_session.json\")",
    "CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"user_session.json\")\n"
    "ADMIN_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"admin_config.json\")\n"
    "ADMIN_USER = \"admin\"\n"
    "ADMIN_PASS = \"fluxgen@2026\""
)

# 2. Add load/save admin config functions after save_session
content = content.replace(
    "def load_session():",
    "def load_admin_config():\n"
    "    global USERNAME, PASSWORD, LOGIN_TYPE\n"
    "    try:\n"
    "        if os.path.exists(ADMIN_CONFIG):\n"
    "            with open(ADMIN_CONFIG) as f:\n"
    "                d = json.load(f)\n"
    "                if d.get(\"api_username\") and d.get(\"api_password\"):\n"
    "                    USERNAME = d[\"api_username\"]\n"
    "                    PASSWORD = d[\"api_password\"]\n"
    "                    LOGIN_TYPE = d.get(\"login_type\", \"DEFAULT\")\n"
    "                    return True\n"
    "    except: pass\n"
    "    return False\n"
    "\n"
    "def save_admin_config(api_user, api_pass, login_type=\"DEFAULT\"):\n"
    "    try:\n"
    "        with open(ADMIN_CONFIG, \"w\") as f:\n"
    "            json.dump({\"api_username\": api_user, \"api_password\": api_pass, \"login_type\": login_type}, f)\n"
    "        return True\n"
    "    except: return False\n"
    "\n"
    "def load_session():"
)

# 3. Add "Admin" button to login page - after keyboard button
content = content.replace(
    "        kb_btn.connect(\"clicked\", self.toggle_keyboard)\n"
    "        box.pack_start(kb_btn, False, False, 0)\n"
    "\n"
    "        outer.pack_start(box, False, False, 0)",

    "        kb_btn.connect(\"clicked\", self.toggle_keyboard)\n"
    "        box.pack_start(kb_btn, False, False, 0)\n"
    "\n"
    "        # Admin settings button\n"
    "        admin_btn = Gtk.Button(label=\"\\u2699  Admin Settings\")\n"
    "        admin_btn.modify_font(Pango.FontDescription(\"Sans 9\"))\n"
    "        admin_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 0.7))\n"
    "        admin_btn.set_margin_start(30)\n"
    "        admin_btn.set_margin_end(30)\n"
    "        admin_btn.set_margin_bottom(15)\n"
    "        admin_btn.connect(\"clicked\", self._open_admin)\n"
    "        box.pack_start(admin_btn, False, False, 0)\n"
    "\n"
    "        outer.pack_start(box, False, False, 0)"
)

# 4. Add _open_admin method and AdminWindow class before toggle_keyboard
ADMIN_CODE = '''    def _open_admin(self, button):
        """Open admin login dialog."""
        dialog = Gtk.Dialog(title="Admin Login", parent=self, flags=0)
        dialog.set_default_size(350, 200)
        dialog.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)

        title = Gtk.Label(label="Admin Login")
        title.modify_font(Pango.FontDescription("Sans bold 14"))
        box.pack_start(title, False, False, 0)

        al = Gtk.Label(label="Admin Username")
        al.modify_font(Pango.FontDescription("Sans bold 10"))
        al.set_halign(Gtk.Align.START)
        box.pack_start(al, False, False, 0)
        admin_user = Gtk.Entry()
        admin_user.set_placeholder_text("Admin username")
        box.pack_start(admin_user, False, False, 0)

        pl = Gtk.Label(label="Admin Password")
        pl.modify_font(Pango.FontDescription("Sans bold 10"))
        pl.set_halign(Gtk.Align.START)
        box.pack_start(pl, False, False, 0)
        admin_pass = Gtk.Entry()
        admin_pass.set_placeholder_text("Admin password")
        admin_pass.set_visibility(False)
        box.pack_start(admin_pass, False, False, 0)

        err = Gtk.Label(label="")
        err.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
        box.pack_start(err, False, False, 0)

        def on_admin_login(btn):
            u = admin_user.get_text().strip()
            p = admin_pass.get_text().strip()
            if u == ADMIN_USER and p == ADMIN_PASS:
                dialog.destroy()
                self._show_admin_settings()
            else:
                err.set_text("Wrong admin credentials")

        login_btn = Gtk.Button(label="Login")
        login_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.69, 1))
        login_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        login_btn.modify_font(Pango.FontDescription("Sans bold 12"))
        login_btn.connect("clicked", on_admin_login)
        box.pack_start(login_btn, False, False, 5)

        dialog.show_all()

    def _show_admin_settings(self):
        """Show admin settings page to configure API credentials."""
        dialog = Gtk.Dialog(title="Admin Settings", parent=self, flags=0)
        dialog.set_default_size(400, 350)
        dialog.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))

        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(10)

        title = Gtk.Label(label="API Configuration")
        title.modify_font(Pango.FontDescription("Sans bold 16"))
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.15, 0.35, 1))
        box.pack_start(title, False, False, 0)

        sub = Gtk.Label(label="Configure the username and password for AquaGen API")
        sub.modify_font(Pango.FontDescription("Sans 9"))
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 1))
        box.pack_start(sub, False, False, 4)

        sep = Gtk.Separator()
        box.pack_start(sep, False, False, 6)

        # API Username
        ul = Gtk.Label(label="API Username")
        ul.modify_font(Pango.FontDescription("Sans bold 11"))
        ul.set_halign(Gtk.Align.START)
        box.pack_start(ul, False, False, 0)
        api_user_entry = Gtk.Entry()
        api_user_entry.set_text(USERNAME)
        api_user_entry.modify_font(Pango.FontDescription("Sans 12"))
        box.pack_start(api_user_entry, False, False, 0)

        # API Password
        ppl = Gtk.Label(label="API Password")
        ppl.modify_font(Pango.FontDescription("Sans bold 11"))
        ppl.set_halign(Gtk.Align.START)
        box.pack_start(ppl, False, False, 0)
        api_pass_entry = Gtk.Entry()
        api_pass_entry.set_text(PASSWORD)
        api_pass_entry.modify_font(Pango.FontDescription("Sans 12"))
        box.pack_start(api_pass_entry, False, False, 0)

        # Login Type
        ltl = Gtk.Label(label="Login Type")
        ltl.modify_font(Pango.FontDescription("Sans bold 11"))
        ltl.set_halign(Gtk.Align.START)
        box.pack_start(ltl, False, False, 0)
        lt_combo = Gtk.ComboBoxText()
        lt_combo.append_text("DEFAULT")
        lt_combo.append_text("EXTERNAL")
        lt_combo.set_active(0 if LOGIN_TYPE == "DEFAULT" else 1)
        box.pack_start(lt_combo, False, False, 0)

        status = Gtk.Label(label="")
        status.modify_font(Pango.FontDescription("Sans bold 11"))
        box.pack_start(status, False, False, 4)

        def on_save(btn):
            global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time
            new_user = api_user_entry.get_text().strip()
            new_pass = api_pass_entry.get_text().strip()
            new_lt = lt_combo.get_active_text()

            if not new_user or not new_pass:
                status.set_text("Enter both username and password")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
                return

            USERNAME = new_user
            PASSWORD = new_pass
            LOGIN_TYPE = new_lt
            token = ""
            token_time = 0

            if save_admin_config(new_user, new_pass, new_lt):
                save_session()
                status.set_text("Saved! API credentials updated.")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
            else:
                status.set_text("Save failed!")
                status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))

        def on_test(btn):
            global USERNAME, PASSWORD, LOGIN_TYPE, token, token_time
            old_u, old_p, old_lt = USERNAME, PASSWORD, LOGIN_TYPE
            USERNAME = api_user_entry.get_text().strip()
            PASSWORD = api_pass_entry.get_text().strip()
            LOGIN_TYPE = lt_combo.get_active_text()
            token = ""
            token_time = 0

            status.set_text("Testing...")
            status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.3, 0.7, 1))

            def do_test():
                success = get_token()
                def show_result(ok):
                    if ok:
                        status.set_text("Connection successful!")
                        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
                    else:
                        status.set_text("Connection failed! Check credentials.")
                        status.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
                        global USERNAME, PASSWORD, LOGIN_TYPE
                        USERNAME, PASSWORD, LOGIN_TYPE = old_u, old_p, old_lt
                GLib.idle_add(show_result, success)
            threading.Thread(target=do_test, daemon=True).start()

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        test_btn = Gtk.Button(label="Test Connection")
        test_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.5, 0.8, 1))
        test_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        test_btn.modify_font(Pango.FontDescription("Sans bold 11"))
        test_btn.connect("clicked", on_test)
        btn_box.pack_start(test_btn, True, True, 0)

        save_btn = Gtk.Button(label="Save")
        save_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.6, 0.2, 1))
        save_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        save_btn.modify_font(Pango.FontDescription("Sans bold 11"))
        save_btn.connect("clicked", on_save)
        btn_box.pack_start(save_btn, True, True, 0)

        box.pack_start(btn_box, False, False, 5)

        close_btn = Gtk.Button(label="Close")
        close_btn.modify_font(Pango.FontDescription("Sans 10"))
        close_btn.connect("clicked", lambda b: dialog.destroy())
        box.pack_start(close_btn, False, False, 0)

        dialog.show_all()

'''

content = content.replace(
    "    def toggle_keyboard(self, button):",
    ADMIN_CODE + "    def toggle_keyboard(self, button):"
)

# 5. Load admin config on startup (before load_session)
content = content.replace(
    "    load_session()",
    "    load_admin_config()\n    load_session()"
)

# 6. Also load admin config when login succeeds
content = content.replace(
    "            LOGGED_IN = True\n            save_session()",
    "            LOGGED_IN = True\n            save_session()\n            save_admin_config(USERNAME, PASSWORD, LOGIN_TYPE)"
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('rm -f /home/aquabox/Desktop/Aquabox/user_session.json')
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command('journalctl -u aquabox-alerts.service --no-pager -n 5 2>&1 | grep -i error | grep -v AT-SPI | grep -v Deprecation | head -3')
err = stdout.read().decode('utf-8', errors='replace').strip()
print('Errors:', err if err else 'None')

ssh.close()
print('Done!')
