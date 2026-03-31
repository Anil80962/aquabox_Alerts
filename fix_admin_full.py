import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Replace admin login dialog with fullscreen window
start = content.find('    def _open_admin(self, button):')
end = content.find('    def _show_admin_settings(self):')

NEW_ADMIN = '''    def _open_admin(self, button):
        """Open admin login - fullscreen with animation."""
        self._admin_win = Gtk.Window(title="Admin")
        self._admin_win.set_default_size(800, 480)
        self._admin_win.fullscreen()
        self._admin_win.set_app_paintable(True)

        da = Gtk.DrawingArea()
        da.connect("draw", self._draw_admin_bg)
        overlay = Gtk.Overlay()
        overlay.add(da)
        self._admin_bg_phase = 0
        GLib.timeout_add(50, self._animate_admin_bg, da)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))
        card.set_size_request(350, -1)

        title = Gtk.Label(label="Admin Settings")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.15, 0.35, 1))
        title.modify_font(Pango.FontDescription("Sans bold 16"))
        title.set_margin_top(15)
        card.pack_start(title, False, False, 0)

        sub = Gtk.Label(label="Enter admin credentials")
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.55, 1))
        sub.modify_font(Pango.FontDescription("Sans 9"))
        card.pack_start(sub, False, False, 0)

        sep = Gtk.Separator()
        sep.set_margin_start(25)
        sep.set_margin_end(25)
        sep.set_margin_top(6)
        card.pack_start(sep, False, False, 0)

        ul = Gtk.Label(label="Admin Username")
        ul.modify_font(Pango.FontDescription("Sans bold 10"))
        ul.set_halign(Gtk.Align.START)
        ul.set_margin_start(25)
        ul.set_margin_top(6)
        card.pack_start(ul, False, False, 0)
        admin_user = Gtk.Entry()
        admin_user.set_placeholder_text("Enter admin username")
        admin_user.modify_font(Pango.FontDescription("Sans 11"))
        admin_user.set_margin_start(25)
        admin_user.set_margin_end(25)
        card.pack_start(admin_user, False, False, 0)

        pl = Gtk.Label(label="Admin Password")
        pl.modify_font(Pango.FontDescription("Sans bold 10"))
        pl.set_halign(Gtk.Align.START)
        pl.set_margin_start(25)
        pl.set_margin_top(4)
        card.pack_start(pl, False, False, 0)
        admin_pass = Gtk.Entry()
        admin_pass.set_placeholder_text("Enter admin password")
        admin_pass.set_visibility(False)
        admin_pass.modify_font(Pango.FontDescription("Sans 11"))
        admin_pass.set_margin_start(25)
        admin_pass.set_margin_end(25)
        card.pack_start(admin_pass, False, False, 0)

        err = Gtk.Label(label="")
        err.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.1, 0.1, 1))
        err.modify_font(Pango.FontDescription("Sans bold 9"))
        card.pack_start(err, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_start(25)
        btn_box.set_margin_end(25)
        btn_box.set_margin_bottom(15)

        login_btn = Gtk.Button(label="Login")
        login_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.69, 1))
        login_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        login_btn.modify_font(Pango.FontDescription("Sans bold 12"))

        back_btn = Gtk.Button(label="Back")
        back_btn.modify_font(Pango.FontDescription("Sans 10"))
        back_btn.connect("clicked", lambda b: self._admin_win.destroy())

        def on_admin_login(btn):
            u = admin_user.get_text().strip()
            p = admin_pass.get_text().strip()
            if u == ADMIN_USER and p == ADMIN_PASS:
                self._admin_win.destroy()
                self._show_admin_settings()
            else:
                err.set_text("Wrong admin credentials")

        login_btn.connect("clicked", on_admin_login)
        admin_pass.connect("activate", on_admin_login)
        btn_box.pack_start(login_btn, True, True, 0)
        btn_box.pack_start(back_btn, True, True, 0)
        card.pack_start(btn_box, False, False, 4)

        outer.pack_start(card, False, False, 0)
        overlay.add_overlay(outer)
        self._admin_win.add(overlay)
        self._admin_win.show_all()

    def _animate_admin_bg(self, da):
        self._admin_bg_phase += 0.04
        da.queue_draw()
        if hasattr(self, "_admin_win"):
            try:
                return self._admin_win.get_visible()
            except:
                return False
        return False

    def _draw_admin_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        t = self._admin_bg_phase
        pat = cairo.LinearGradient(0, 0, 0, h)
        pat.add_color_stop_rgb(0, 0.05, 0.12, 0.28)
        pat.add_color_stop_rgb(0.5, 0.08, 0.18, 0.38)
        pat.add_color_stop_rgb(1, 0.04, 0.1, 0.22)
        cr.set_source(pat)
        cr.paint()
        for i, (amp, freq, spd, a) in enumerate([
            (10, 0.02, 1.2, 0.15), (7, 0.025, -0.9, 0.1), (5, 0.03, 1.5, 0.08)
        ]):
            cr.move_to(0, h)
            base_y = h * 0.78 + i * 12
            for x in range(0, w + 2, 3):
                y = base_y + amp * _math.sin(x * freq + t * spd)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            cr.set_source_rgba(0.2, 0.5, 0.8, a)
            cr.fill()

'''

content = content[:start] + NEW_ADMIN + content[end:]

# 2. Make admin settings page fullscreen too
content = content.replace(
    '        dialog = Gtk.Dialog(title="Admin Settings", parent=self, flags=0)\n        dialog.set_default_size(400, 440)',
    '        dialog = Gtk.Window(title="Admin Settings")\n        dialog.set_default_size(800, 480)\n        dialog.fullscreen()'
)

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

ssh.exec_command('rm -f /home/aquabox/Desktop/Aquabox/user_session.json')
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
