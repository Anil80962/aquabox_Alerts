import paramiko, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Add imports if missing
if 'import cairo' not in content:
    content = content.replace(
        'from gi.repository import Gtk, Gdk, GLib, Pango',
        'from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf\nimport cairo, math as _math, random as _random'
    )

# New LoginWindow with logo + water animation
NEW_LOGIN = r'''class LoginWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="AquaBox Login")
        self.set_default_size(800, 480)
        self.fullscreen()
        self.set_app_paintable(True)
        self._kb_visible = False
        self._wave_offset = 0
        self._bubbles = []
        for _ in range(15):
            self._bubbles.append({
                "x": _random.uniform(0, 800), "y": _random.uniform(300, 480),
                "r": _random.uniform(2, 6), "speed": _random.uniform(0.3, 1.2),
                "alpha": _random.uniform(0.1, 0.4)
            })

        da = Gtk.DrawingArea()
        da.connect("draw", self._draw_bg)
        overlay = Gtk.Overlay()
        overlay.add(da)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.92))
        box.set_size_request(380, -1)

        logo_path = "/home/aquabox/Desktop/Aquabox/Fluxgen-Logo.png"
        if os.path.exists(logo_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 200, 60, True)
            logo = Gtk.Image.new_from_pixbuf(pixbuf)
            logo.set_margin_top(15)
            box.pack_start(logo, False, False, 0)

        title = Gtk.Label(label="AquaBox Alerts")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.15, 0.35, 1))
        title.modify_font(Pango.FontDescription("Sans bold 20"))
        box.pack_start(title, False, False, 2)

        sub = Gtk.Label(label="Fluxgen Sustainable Technologies")
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.4, 0.45, 0.52, 1))
        sub.modify_font(Pango.FontDescription("Sans 12"))
        box.pack_start(sub, False, False, 0)

        sep = Gtk.Separator()
        box.pack_start(sep, False, False, 6)

        ulabel = Gtk.Label(label="Username")
        ulabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.2, 0.2, 1))
        ulabel.modify_font(Pango.FontDescription("Sans bold 14"))
        ulabel.set_halign(Gtk.Align.START)
        ulabel.set_margin_start(15)
        box.pack_start(ulabel, False, False, 0)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Enter username")
        self.username_entry.modify_font(Pango.FontDescription("Sans 16"))
        self.username_entry.set_margin_start(15)
        self.username_entry.set_margin_end(15)
        box.pack_start(self.username_entry, False, False, 0)

        plabel = Gtk.Label(label="Password")
        plabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.2, 0.2, 1))
        plabel.modify_font(Pango.FontDescription("Sans bold 14"))
        plabel.set_halign(Gtk.Align.START)
        plabel.set_margin_start(15)
        box.pack_start(plabel, False, False, 0)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_placeholder_text("Enter password")
        self.password_entry.set_visibility(False)
        self.password_entry.modify_font(Pango.FontDescription("Sans 16"))
        self.password_entry.set_margin_start(15)
        self.password_entry.set_margin_end(15)
        self.password_entry.connect("activate", self.on_login)
        box.pack_start(self.password_entry, False, False, 0)

        self.error_label = Gtk.Label(label="")
        self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.86, 0.15, 0.15, 1))
        self.error_label.modify_font(Pango.FontDescription("Sans bold 12"))
        box.pack_start(self.error_label, False, False, 0)

        btn = Gtk.Button(label="Login")
        btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.69, 1))
        btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        btn.modify_font(Pango.FontDescription("Sans bold 16"))
        btn.set_margin_start(15)
        btn.set_margin_end(15)
        btn.connect("clicked", self.on_login)
        box.pack_start(btn, False, False, 4)

        kb_btn = Gtk.Button(label="\u2328  Keyboard")
        kb_btn.modify_font(Pango.FontDescription("Sans 12"))
        kb_btn.set_margin_start(15)
        kb_btn.set_margin_end(15)
        kb_btn.set_margin_bottom(15)
        kb_btn.connect("clicked", self.toggle_keyboard)
        box.pack_start(kb_btn, False, False, 0)

        outer.pack_start(box, False, False, 0)
        overlay.add_overlay(outer)
        self.add(overlay)
        GLib.timeout_add(50, self._animate)

    def _animate(self):
        self._wave_offset += 0.05
        for b in self._bubbles:
            b["y"] -= b["speed"]
            if b["y"] < -10:
                b["y"] = _random.uniform(480, 520)
                b["x"] = _random.uniform(0, 800)
        self.get_child().get_child().queue_draw()
        return True

    def _draw_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        pat = cairo.LinearGradient(0, 0, 0, h)
        pat.add_color_stop_rgb(0, 0.06, 0.18, 0.45)
        pat.add_color_stop_rgb(0.5, 0.08, 0.25, 0.55)
        pat.add_color_stop_rgb(1, 0.04, 0.12, 0.35)
        cr.set_source(pat)
        cr.paint()
        t = self._wave_offset
        for i, (amp, freq, spd, alpha) in enumerate([
            (12, 0.015, 1.0, 0.15), (8, 0.02, -0.7, 0.1), (6, 0.025, 1.3, 0.08)
        ]):
            cr.move_to(0, h)
            base_y = h * 0.75 + i * 15
            for x in range(0, w + 2, 3):
                y = base_y + amp * _math.sin(x * freq + t * spd) + amp * 0.5 * _math.sin(x * freq * 1.5 + t * spd * 0.8)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            cr.set_source_rgba(0.3, 0.6, 0.9, alpha)
            cr.fill()
        for b in self._bubbles:
            cr.arc(b["x"], b["y"], b["r"], 0, _math.pi * 2)
            cr.set_source_rgba(0.5, 0.75, 1.0, b["alpha"])
            cr.fill()
            cr.arc(b["x"] - b["r"] * 0.3, b["y"] - b["r"] * 0.3, b["r"] * 0.3, 0, _math.pi * 2)
            cr.set_source_rgba(1, 1, 1, b["alpha"] * 0.5)
            cr.fill()

    def toggle_keyboard(self, button):
        import subprocess
        if self._kb_visible:
            subprocess.run(["killall", "wvkbd-mobintl"], capture_output=True)
            button.set_label("\u2328  Keyboard")
            self._kb_visible = False
        else:
            env = os.environ.copy()
            env["WAYLAND_DISPLAY"] = "wayland-0"
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            subprocess.Popen(["wvkbd-mobintl", "-L", "300", "--hidden"], env=env)
            time.sleep(0.5)
            subprocess.Popen(["wvkbd-mobintl", "-L", "300"], env=env)
            button.set_label("\u2328  Hide Keyboard")
            self._kb_visible = True
'''

# Find and replace the old LoginWindow class
import re
# Match from "class LoginWindow" to just before "class AlertsWindow"
pattern = r'class LoginWindow\(Gtk\.Window\):.*?(?=class AlertsWindow\(Gtk\.Window\):)'
# Use string find/replace instead of regex to avoid escape issues
start_idx = content.find('class LoginWindow(Gtk.Window):')
end_idx = content.find('class AlertsWindow(Gtk.Window):')
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + NEW_LOGIN + '\n\n' + content[end_idx:]
else:
    print('ERROR: Could not find LoginWindow or AlertsWindow class')

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Delete session
ssh.exec_command('rm -f /home/aquabox/Desktop/Aquabox/user_session.json')

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
ssh.exec_command('killall wvkbd-mobintl 2>/dev/null')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command('journalctl -u aquabox-alerts.service --no-pager -n 5 2>&1 | grep -iE "error|trace" | grep -v AT-SPI | grep -v Deprecation | head -3')
err = stdout.read().decode('utf-8', errors='replace').strip()
print('Errors:', err if err else 'None')

ssh.close()
print('Done!')
