import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Add panda mascot overlay to AlertsWindow
# Add a DrawingArea overlay for the panda in bottom-right

# Find where overlay is set up in AlertsWindow
# Add panda after the announce overlay setup

PANDA_CODE = '''
        # AquaGPT Panda Mascot
        self._panda_da = Gtk.DrawingArea()
        self._panda_da.set_size_request(220, 150)
        self._panda_da.set_halign(Gtk.Align.END)
        self._panda_da.set_valign(Gtk.Align.END)
        self._panda_da.set_margin_end(10)
        self._panda_da.set_margin_bottom(30)
        self._panda_da.connect("draw", self._draw_panda)
        self._panda_da.set_no_show_all(True)
        self._panda_da.set_visible(False)
        overlay.add_overlay(self._panda_da)

        self._panda_phase = 0
        self._panda_visible = False
        self._panda_alpha = 0.0
        self._panda_msg_idx = 0
        self._panda_msg_char = 0
        self._panda_messages = [
            "Hi! I am AquaGPT",
            "Your water assistant!",
            "Monitoring your alerts",
            "Stay water positive!",
            "Need help? I am here!",
        ]
        self._panda_current_msg = ""

        # Show panda every 60 seconds
        GLib.timeout_add_seconds(60, self._show_panda)
        GLib.timeout_add(50, self._animate_panda)
'''

content = content.replace(
    '        # Start fetching',
    PANDA_CODE + '\n        # Start fetching'
)

# 2. Add panda drawing and animation methods
PANDA_METHODS = '''
    def _show_panda(self):
        """Show panda mascot popup."""
        if _auto_announcing:
            return True  # Skip during announce
        self._panda_visible = True
        self._panda_alpha = 0.0
        self._panda_msg_char = 0
        self._panda_current_msg = self._panda_messages[self._panda_msg_idx % len(self._panda_messages)]
        self._panda_msg_idx += 1
        self._panda_da.set_visible(True)
        self._panda_da.show()
        # Auto-hide after 8 seconds
        GLib.timeout_add_seconds(8, self._hide_panda)
        return True  # Keep timer

    def _hide_panda(self):
        self._panda_visible = False
        GLib.timeout_add(50, self._fade_panda_out)
        return False

    def _fade_panda_out(self):
        self._panda_alpha -= 0.05
        if self._panda_alpha <= 0:
            self._panda_da.set_visible(False)
            self._panda_da.hide()
            return False
        self._panda_da.queue_draw()
        return True

    def _animate_panda(self):
        if self._panda_visible:
            self._panda_phase += 0.08
            if self._panda_alpha < 1.0:
                self._panda_alpha = min(1.0, self._panda_alpha + 0.05)
            if self._panda_msg_char < len(self._panda_current_msg):
                self._panda_msg_char += 1
            self._panda_da.queue_draw()
        return True

    def _draw_panda(self, widget, cr):
        if self._panda_alpha <= 0:
            return
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        a = self._panda_alpha

        # Speech bubble
        cr.save()
        # Bubble background
        bx, by, bw, bh = 5, 5, w - 10, 50
        cr.set_source_rgba(1, 1, 1, a * 0.95)
        cr.move_to(bx + 10, by)
        cr.line_to(bx + bw - 10, by)
        cr.curve_to(bx + bw, by, bx + bw, by, bx + bw, by + 10)
        cr.line_to(bx + bw, by + bh - 10)
        cr.curve_to(bx + bw, by + bh, bx + bw, by + bh, bx + bw - 10, by + bh)
        cr.line_to(bx + bw * 0.7 + 10, by + bh)
        cr.line_to(bx + bw * 0.7, by + bh + 12)
        cr.line_to(bx + bw * 0.7 - 10, by + bh)
        cr.line_to(bx + 10, by + bh)
        cr.curve_to(bx, by + bh, bx, by + bh, bx, by + bh - 10)
        cr.line_to(bx, by + 10)
        cr.curve_to(bx, by, bx, by, bx + 10, by)
        cr.close_path()
        cr.fill()

        # Bubble border
        cr.set_source_rgba(0.2, 0.5, 0.8, a * 0.5)
        cr.set_line_width(1.5)
        cr.move_to(bx + 10, by)
        cr.line_to(bx + bw - 10, by)
        cr.curve_to(bx + bw, by, bx + bw, by, bx + bw, by + 10)
        cr.line_to(bx + bw, by + bh - 10)
        cr.curve_to(bx + bw, by + bh, bx + bw, by + bh, bx + bw - 10, by + bh)
        cr.line_to(bx + bw * 0.7 + 10, by + bh)
        cr.line_to(bx + bw * 0.7, by + bh + 12)
        cr.line_to(bx + bw * 0.7 - 10, by + bh)
        cr.line_to(bx + 10, by + bh)
        cr.curve_to(bx, by + bh, bx, by + bh, bx, by + bh - 10)
        cr.line_to(bx, by + 10)
        cr.curve_to(bx, by, bx, by, bx + 10, by)
        cr.close_path()
        cr.stroke()

        # Message text with typing effect
        msg = self._panda_current_msg[:self._panda_msg_char]
        cr.set_source_rgba(0.1, 0.2, 0.4, a)
        cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12)
        ext = cr.text_extents(msg)
        cr.move_to(bx + (bw - ext.width) / 2, by + 30)
        cr.show_text(msg)

        # "AquaGPT" label
        cr.set_source_rgba(0.08, 0.4, 0.75, a * 0.7)
        cr.set_font_size(9)
        cr.move_to(bx + 10, by + 46)
        cr.show_text("AquaGPT")
        cr.restore()

        # Panda body position
        px = w * 0.7
        py = h - 40
        bounce = _math.sin(self._panda_phase * 2) * 3

        cr.save()
        cr.translate(px, py + bounce)

        # Body (white oval)
        cr.set_source_rgba(1, 1, 1, a)
        cr.save()
        cr.scale(1, 1.2)
        cr.arc(0, -8, 22, 0, _math.pi * 2)
        cr.restore()
        cr.fill()

        # Head (white circle)
        cr.set_source_rgba(1, 1, 1, a)
        cr.arc(0, -38, 20, 0, _math.pi * 2)
        cr.fill()

        # Ears (black)
        cr.set_source_rgba(0.1, 0.1, 0.1, a)
        cr.arc(-15, -52, 8, 0, _math.pi * 2)
        cr.fill()
        cr.arc(15, -52, 8, 0, _math.pi * 2)
        cr.fill()

        # Inner ears (dark gray)
        cr.set_source_rgba(0.3, 0.3, 0.3, a)
        cr.arc(-15, -52, 5, 0, _math.pi * 2)
        cr.fill()
        cr.arc(15, -52, 5, 0, _math.pi * 2)
        cr.fill()

        # Eye patches (black)
        cr.set_source_rgba(0.1, 0.1, 0.1, a)
        cr.save()
        cr.translate(-8, -40)
        cr.scale(1, 0.8)
        cr.arc(0, 0, 7, 0, _math.pi * 2)
        cr.restore()
        cr.fill()
        cr.save()
        cr.translate(8, -40)
        cr.scale(1, 0.8)
        cr.arc(0, 0, 7, 0, _math.pi * 2)
        cr.restore()
        cr.fill()

        # Eyes (white)
        blink = abs(_math.sin(self._panda_phase * 0.5))
        eye_h = max(0.3, blink)
        cr.set_source_rgba(1, 1, 1, a)
        cr.save()
        cr.translate(-8, -40)
        cr.scale(1, eye_h)
        cr.arc(0, 0, 3.5, 0, _math.pi * 2)
        cr.restore()
        cr.fill()
        cr.save()
        cr.translate(8, -40)
        cr.scale(1, eye_h)
        cr.arc(0, 0, 3.5, 0, _math.pi * 2)
        cr.restore()
        cr.fill()

        # Pupils
        cr.set_source_rgba(0.05, 0.05, 0.2, a)
        cr.arc(-7, -40, 2, 0, _math.pi * 2)
        cr.fill()
        cr.arc(9, -40, 2, 0, _math.pi * 2)
        cr.fill()

        # Nose
        cr.set_source_rgba(0.15, 0.15, 0.15, a)
        cr.save()
        cr.translate(0, -33)
        cr.scale(1, 0.7)
        cr.arc(0, 0, 3, 0, _math.pi * 2)
        cr.restore()
        cr.fill()

        # Mouth (smile)
        cr.set_source_rgba(0.15, 0.15, 0.15, a)
        cr.set_line_width(1.2)
        cr.arc(0, -30, 5, 0.2, _math.pi - 0.2)
        cr.stroke()

        # Arms (black)
        cr.set_source_rgba(0.1, 0.1, 0.1, a)
        wave = _math.sin(self._panda_phase * 3) * 0.3
        # Left arm
        cr.save()
        cr.translate(-20, -12)
        cr.rotate(-0.4 + wave)
        cr.save()
        cr.scale(1, 2.5)
        cr.arc(0, 0, 5, 0, _math.pi * 2)
        cr.restore()
        cr.fill()
        cr.restore()
        # Right arm (waving)
        cr.save()
        cr.translate(20, -12)
        cr.rotate(0.4 - wave * 2)
        cr.save()
        cr.scale(1, 2.5)
        cr.arc(0, 0, 5, 0, _math.pi * 2)
        cr.restore()
        cr.fill()
        cr.restore()

        # Legs (black)
        cr.set_source_rgba(0.1, 0.1, 0.1, a)
        cr.save()
        cr.scale(1, 0.7)
        cr.arc(-10, 18, 7, 0, _math.pi * 2)
        cr.restore()
        cr.fill()
        cr.save()
        cr.scale(1, 0.7)
        cr.arc(10, 18, 7, 0, _math.pi * 2)
        cr.restore()
        cr.fill()

        # Water drop on belly (blue)
        cr.set_source_rgba(0.2, 0.5, 0.9, a * 0.6)
        s = 6
        cr.move_to(0, -15)
        cr.curve_to(s * 0.5, -8, s * 0.7, -3, 0, 0)
        cr.curve_to(-s * 0.7, -3, -s * 0.5, -8, 0, -15)
        cr.fill()

        cr.restore()

'''

content = content.replace(
    '    def _scroll_to_section(self, section):',
    PANDA_METHODS + '    def _scroll_to_section(self, section):'
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
result = stdout.read().decode('utf-8', errors='replace').strip()
print(result)

if 'SYNTAX OK' in result:
    ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
    ssh.exec_command('killall aplay 2>/dev/null')
    time.sleep(2)
    ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
    print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
