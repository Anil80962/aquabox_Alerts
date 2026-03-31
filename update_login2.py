import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# Find LoginWindow class boundaries
start = content.find('class LoginWindow(Gtk.Window):')
end = content.find('    def on_login(self, widget):')

if start == -1 or end == -1:
    print('ERROR: Could not find LoginWindow')
    sys.exit(1)

NEW_LOGIN = r'''class LoginWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="AquaBox Login")
        self.set_default_size(800, 480)
        self.fullscreen()
        self.set_app_paintable(True)
        self._kb_visible = False
        self._wave_offset = 0
        self._pulse = 0
        self._drops = []
        self._ripples = []
        self._last_ripple = 0
        for _ in range(30):
            self._drops.append({
                "x": _random.uniform(0, 800), "y": _random.uniform(-50, 480),
                "r": _random.uniform(2, 7), "speed": _random.uniform(1.0, 3.0),
                "alpha": _random.uniform(0.15, 0.45),
                "wobble": _random.uniform(0.5, 2.0), "phase": _random.uniform(0, 6.28)
            })

        # Background drawing
        da = Gtk.DrawingArea()
        da.connect("draw", self._draw_bg)
        overlay = Gtk.Overlay()
        overlay.add(da)

        # Main centered container
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        # Card with rounded feel
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 0.95))
        card.set_size_request(420, -1)

        # Top accent bar (blue gradient line)
        accent = Gtk.DrawingArea()
        accent.set_size_request(-1, 6)
        accent.connect("draw", self._draw_accent)
        card.pack_start(accent, False, False, 0)

        # Logo section
        logo_path = "/home/aquabox/Desktop/Aquabox/Fluxgen-Logo.png"
        if os.path.exists(logo_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 180, 55, True)
            logo = Gtk.Image.new_from_pixbuf(pixbuf)
            logo.set_margin_top(20)
            card.pack_start(logo, False, False, 0)

        # Title
        title = Gtk.Label(label="AquaBox Alerts")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.07, 0.13, 0.32, 1))
        title.modify_font(Pango.FontDescription("Sans bold 22"))
        title.set_margin_top(8)
        card.pack_start(title, False, False, 0)

        # Subtitle
        sub = Gtk.Label(label="Fluxgen Sustainable Technologies")
        sub.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.35, 0.42, 0.52, 1))
        sub.modify_font(Pango.FontDescription("Sans 11"))
        card.pack_start(sub, False, False, 2)

        # Tagline
        tag = Gtk.Label(label="Build a Water-Positive Future")
        tag.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.2, 0.5, 0.8, 0.7))
        tag.modify_font(Pango.FontDescription("Sans italic 9"))
        card.pack_start(tag, False, False, 2)

        # Divider
        div = Gtk.DrawingArea()
        div.set_size_request(-1, 2)
        div.set_margin_start(30)
        div.set_margin_end(30)
        div.set_margin_top(10)
        div.set_margin_bottom(8)
        div.connect("draw", self._draw_divider)
        card.pack_start(div, False, False, 0)

        # Sign In label
        signin = Gtk.Label(label="Sign In")
        signin.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.2, 0.4, 1))
        signin.modify_font(Pango.FontDescription("Sans bold 16"))
        signin.set_halign(Gtk.Align.START)
        signin.set_margin_start(30)
        card.pack_start(signin, False, False, 0)

        # Username
        ulabel = Gtk.Label(label="Username")
        ulabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.3, 0.35, 0.4, 1))
        ulabel.modify_font(Pango.FontDescription("Sans bold 12"))
        ulabel.set_halign(Gtk.Align.START)
        ulabel.set_margin_start(30)
        ulabel.set_margin_top(8)
        card.pack_start(ulabel, False, False, 0)

        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Enter your username")
        self.username_entry.modify_font(Pango.FontDescription("Sans 14"))
        self.username_entry.set_margin_start(30)
        self.username_entry.set_margin_end(30)
        card.pack_start(self.username_entry, False, False, 4)

        # Password
        plabel = Gtk.Label(label="Password")
        plabel.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.3, 0.35, 0.4, 1))
        plabel.modify_font(Pango.FontDescription("Sans bold 12"))
        plabel.set_halign(Gtk.Align.START)
        plabel.set_margin_start(30)
        plabel.set_margin_top(6)
        card.pack_start(plabel, False, False, 0)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_placeholder_text("Enter your password")
        self.password_entry.set_visibility(False)
        self.password_entry.modify_font(Pango.FontDescription("Sans 14"))
        self.password_entry.set_margin_start(30)
        self.password_entry.set_margin_end(30)
        self.password_entry.connect("activate", self.on_login)
        card.pack_start(self.password_entry, False, False, 4)

        # Error label
        self.error_label = Gtk.Label(label="")
        self.error_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.85, 0.15, 0.15, 1))
        self.error_label.modify_font(Pango.FontDescription("Sans bold 11"))
        card.pack_start(self.error_label, False, False, 2)

        # Login button
        btn = Gtk.Button(label="Login")
        btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.69, 1))
        btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        btn.modify_font(Pango.FontDescription("Sans bold 16"))
        btn.set_margin_start(30)
        btn.set_margin_end(30)
        btn.set_margin_top(6)
        btn.connect("clicked", self.on_login)
        card.pack_start(btn, False, False, 0)

        # Keyboard button
        kb_btn = Gtk.Button(label="\u2328  Keyboard")
        kb_btn.modify_font(Pango.FontDescription("Sans 11"))
        kb_btn.set_margin_start(30)
        kb_btn.set_margin_end(30)
        kb_btn.set_margin_top(6)
        kb_btn.set_margin_bottom(18)
        kb_btn.connect("clicked", self.toggle_keyboard)
        card.pack_start(kb_btn, False, False, 0)

        outer.pack_start(card, False, False, 0)
        overlay.add_overlay(outer)
        self.add(overlay)
        GLib.timeout_add(40, self._animate)

    def _draw_accent(self, widget, cr):
        w = widget.get_allocated_width()
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgb(0, 0.08, 0.35, 0.8)
        pat.add_color_stop_rgb(0.5, 0.15, 0.55, 0.95)
        pat.add_color_stop_rgb(1, 0.08, 0.35, 0.8)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, 6)
        cr.fill()

    def _draw_divider(self, widget, cr):
        w = widget.get_allocated_width()
        pat = cairo.LinearGradient(0, 0, w, 0)
        pat.add_color_stop_rgba(0, 0.8, 0.85, 0.9, 0)
        pat.add_color_stop_rgba(0.3, 0.7, 0.78, 0.88, 0.6)
        pat.add_color_stop_rgba(0.5, 0.4, 0.6, 0.85, 0.8)
        pat.add_color_stop_rgba(0.7, 0.7, 0.78, 0.88, 0.6)
        pat.add_color_stop_rgba(1, 0.8, 0.85, 0.9, 0)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, 2)
        cr.fill()

    def _animate(self):
        self._wave_offset += 0.04
        self._pulse += 0.02
        now_t = time.time()
        for d in self._drops:
            d["y"] -= d["speed"]
            d["x"] += _math.sin(now_t * d["wobble"] + d["phase"]) * 0.5
            if d["y"] < -15:
                d["y"] = _random.uniform(480, 550)
                d["x"] = _random.uniform(0, 800)
        if now_t - self._last_ripple > 0.8:
            self._ripples.append({"x": _random.uniform(50, 750), "y": _random.uniform(340, 440), "r": 0, "max": _random.uniform(30, 60), "alpha": 0.3})
            self._last_ripple = now_t
        self._ripples = [r for r in self._ripples if r["r"] < r["max"]]
        for r in self._ripples:
            r["r"] += 1.2
        self.get_child().get_child().queue_draw()
        return True

    def _draw_bg(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # White background
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.paint()

        t = self._wave_offset

        # Waves at bottom
        for i, (amp, freq, spd, r, g, b_c, alpha) in enumerate([
            (12, 0.018, 1.2, 0.3, 0.65, 0.92, 0.28),
            (8, 0.022, -0.9, 0.4, 0.72, 0.95, 0.2),
            (6, 0.028, 1.5, 0.35, 0.6, 0.88, 0.15),
        ]):
            cr.move_to(0, h)
            base_y = h * 0.76 + i * 14
            for x in range(0, w + 2, 3):
                y = base_y + amp * _math.sin(x * freq + t * spd) + amp * 0.5 * _math.sin(x * freq * 1.7 + t * spd * 0.8 + 1.3)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            pat = cairo.LinearGradient(0, base_y - amp, 0, h)
            pat.add_color_stop_rgba(0, r, g, b_c, alpha * 0.5)
            pat.add_color_stop_rgba(1, r * 0.7, g * 0.8, b_c * 0.9, alpha)
            cr.set_source(pat)
            cr.fill()

        # Water drops
        for d in self._drops:
            s = d["r"]
            cr.save()
            cr.translate(d["x"], d["y"])
            pat = cairo.RadialGradient(0, s * 0.3, 0, 0, 0, s)
            pat.add_color_stop_rgba(0, 0.65, 0.88, 1.0, d["alpha"] * 0.9)
            pat.add_color_stop_rgba(0.5, 0.4, 0.72, 0.95, d["alpha"] * 0.5)
            pat.add_color_stop_rgba(1.0, 0.2, 0.55, 0.88, d["alpha"] * 0.1)
            cr.set_source(pat)
            cr.move_to(0, -s * 1.2)
            cr.curve_to(s * 0.6, -s * 0.3, s * 0.8, s * 0.4, 0, s)
            cr.curve_to(-s * 0.8, s * 0.4, -s * 0.6, -s * 0.3, 0, -s * 1.2)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, d["alpha"] * 0.6)
            cr.arc(-s * 0.15, -s * 0.2, s * 0.2, 0, _math.pi * 2)
            cr.fill()
            cr.restore()

        # Ripples
        for r in self._ripples:
            progress = r["r"] / r["max"]
            alpha = r["alpha"] * (1.0 - progress)
            if alpha > 0.01:
                cr.set_source_rgba(0.4, 0.72, 0.95, alpha)
                cr.set_line_width(1.5 * (1.0 - progress * 0.5))
                cr.arc(r["x"], r["y"], r["r"], 0, _math.pi * 2)
                cr.stroke()

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
            subprocess.Popen(["wvkbd-mobintl", "-L", "300"], env=env)
            button.set_label("\u2328  Hide Keyboard")
            self._kb_visible = True

'''

content = content[:start] + NEW_LOGIN + content[end:]

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

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

stdin, stdout, stderr = ssh.exec_command('journalctl -u aquabox-alerts.service --no-pager -n 5 2>&1 | grep -i error | grep -v AT-SPI | grep -v Deprecation | head -3')
err = stdout.read().decode('utf-8', errors='replace').strip()
print('Errors:', err if err else 'None')

ssh.close()
print('Done!')
