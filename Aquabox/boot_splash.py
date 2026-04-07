#!/usr/bin/env python3
"""Boot splash - shows Fluxgen logo with water animation until desktop is ready."""
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import os, sys, time, math, random, cairo, signal, threading

LOGO_PATH = "/home/aquabox/Desktop/logo/Fluxgen-Logo.png"
MAX_DURATION = 30  # Max seconds to show

class BootSplash(Gtk.Window):
    def __init__(self):
        super().__init__(title="Boot")
        self.set_decorated(False)
        self.fullscreen()
        self.set_app_paintable(True)
        screen = Gdk.Screen.get_default()
        self.sw = screen.get_width()
        self.sh = screen.get_height()
        self.start_time = time.time()
        self.alpha = 0.0
        self._wave_offset = 0

        # Load logo
        if os.path.exists(LOGO_PATH):
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                LOGO_PATH, int(self.sw * 0.4), int(self.sh * 0.3), True)
        else:
            self.pixbuf = None

        # Water drops
        self.drops = []
        for _ in range(25):
            self.drops.append({
                "x": random.uniform(0, self.sw),
                "y": random.uniform(-50, self.sh),
                "r": random.uniform(2, 7),
                "speed": random.uniform(1.0, 3.0),
                "alpha": random.uniform(0.15, 0.45),
                "wobble": random.uniform(0.5, 2.0),
                "phase": random.uniform(0, 6.28)
            })

        self.da = Gtk.DrawingArea()
        self.da.connect("draw", self.on_draw)
        self.add(self.da)
        GLib.timeout_add(30, self.animate)

        # Auto-close after MAX_DURATION or when alerts app starts
        threading.Thread(target=self._wait_for_app, daemon=True).start()

    def _wait_for_app(self):
        """Wait for aquabox_alerts to start, then close splash."""
        import subprocess
        for _ in range(MAX_DURATION * 2):
            result = subprocess.run(["pgrep", "-f", "aquabox_alerts"], capture_output=True)
            if result.returncode == 0:
                time.sleep(1)
                GLib.idle_add(self._fade_and_close)
                return
            time.sleep(0.5)
        GLib.idle_add(self._fade_and_close)

    def _fade_and_close(self):
        self.destroy()
        Gtk.main_quit()

    def animate(self):
        elapsed = time.time() - self.start_time
        self._wave_offset += 0.04

        if elapsed < 1.5:
            self.alpha = min(1.0, elapsed / 1.5)
        else:
            self.alpha = 1.0

        for d in self.drops:
            d["y"] -= d["speed"]
            d["x"] += math.sin(time.time() * d["wobble"] + d["phase"]) * 0.5
            if d["y"] < -15:
                d["y"] = random.uniform(self.sh, self.sh + 50)
                d["x"] = random.uniform(0, self.sw)

        self.da.queue_draw()
        return True

    def on_draw(self, widget, cr):
        w, h = self.sw, self.sh
        t = self._wave_offset

        # White background
        cr.set_source_rgb(1, 1, 1)
        cr.paint()

        # Water waves
        for i, (amp, freq, spd, r, g, b, a) in enumerate([
            (12, 0.018, 1.2, 0.3, 0.65, 0.92, 0.28),
            (8, 0.022, -0.9, 0.4, 0.72, 0.95, 0.2),
            (6, 0.028, 1.5, 0.35, 0.6, 0.88, 0.15),
        ]):
            cr.move_to(0, h)
            base_y = h * 0.76 + i * 14
            for x in range(0, w + 2, 3):
                y = base_y + amp * math.sin(x * freq + t * spd) + amp * 0.5 * math.sin(x * freq * 1.7 + t * spd * 0.8 + 1.3)
                cr.line_to(x, y)
            cr.line_to(w, h)
            cr.close_path()
            pat = cairo.LinearGradient(0, base_y - amp, 0, h)
            pat.add_color_stop_rgba(0, r, g, b, a * 0.5 * self.alpha)
            pat.add_color_stop_rgba(1, r * 0.7, g * 0.8, b * 0.9, a * self.alpha)
            cr.set_source(pat)
            cr.fill()

        # Water drops
        for d in self.drops:
            s = d["r"]
            cr.save()
            cr.translate(d["x"], d["y"])
            pat = cairo.RadialGradient(0, s * 0.3, 0, 0, 0, s)
            pat.add_color_stop_rgba(0, 0.65, 0.88, 1.0, d["alpha"] * self.alpha * 0.9)
            pat.add_color_stop_rgba(1, 0.2, 0.55, 0.88, d["alpha"] * self.alpha * 0.1)
            cr.set_source(pat)
            cr.move_to(0, -s * 1.2)
            cr.curve_to(s * 0.6, -s * 0.3, s * 0.8, s * 0.4, 0, s)
            cr.curve_to(-s * 0.8, s * 0.4, -s * 0.6, -s * 0.3, 0, -s * 1.2)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, d["alpha"] * self.alpha * 0.6)
            cr.arc(-s * 0.15, -s * 0.2, s * 0.2, 0, math.pi * 2)
            cr.fill()
            cr.restore()

        # Logo
        if self.pixbuf and self.alpha > 0.1:
            lw = self.pixbuf.get_width()
            lh = self.pixbuf.get_height()
            x = (w - lw) / 2
            y = (h - lh) / 2 - h * 0.08
            Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, x, y)
            cr.paint_with_alpha(self.alpha)

            # Welcome text
            cr.set_source_rgba(0.07, 0.15, 0.35, self.alpha * 0.9)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(22)
            txt = "Welcome to AquaBox"
            ext = cr.text_extents(txt)
            cr.move_to((w - ext.width) / 2, y + lh + 35)
            cr.show_text(txt)

            # Powered by
            cr.set_source_rgba(0.35, 0.42, 0.52, self.alpha * 0.7)
            cr.set_font_size(14)
            txt2 = "Powered by Fluxgen"
            ext2 = cr.text_extents(txt2)
            cr.move_to((w - ext2.width) / 2, y + lh + 58)
            cr.show_text(txt2)

            # Tagline
            cr.set_source_rgba(0.3, 0.55, 0.8, self.alpha * 0.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(11)
            txt3 = "Build a Water-Positive Future"
            ext3 = cr.text_extents(txt3)
            cr.move_to((w - ext3.width) / 2, y + lh + 78)
            cr.show_text(txt3)

            # Loading dots
            dots = "." * (int(time.time() * 2) % 4)
            cr.set_source_rgba(0.5, 0.55, 0.65, self.alpha * 0.6)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(13)
            txt4 = "Loading" + dots
            ext4 = cr.text_extents(txt4)
            cr.move_to((w - ext4.width) / 2, y + lh + 105)
            cr.show_text(txt4)

if __name__ == "__main__":
    os.environ["WAYLAND_DISPLAY"] = "wayland-0"
    os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
    os.environ["GDK_BACKEND"] = "wayland"
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    win = BootSplash()
    win.show_all()
    Gtk.main()
