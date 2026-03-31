import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Make water drop clickable - wrap in EventBox
content = content.replace(
    '        self._panda_da = Gtk.DrawingArea()',
    '        self._panda_event = Gtk.EventBox()\n'
    '        self._panda_da = Gtk.DrawingArea()'
)

content = content.replace(
    '        self._panda_da.connect("draw", self._draw_panda)\n'
    '        # Always visible on screen\n'
    '        overlay.add_overlay(self._panda_da)',
    '        self._panda_da.connect("draw", self._draw_panda)\n'
    '        self._panda_event.add(self._panda_da)\n'
    '        self._panda_event.set_halign(Gtk.Align.END)\n'
    '        self._panda_event.set_valign(Gtk.Align.END)\n'
    '        self._panda_event.set_size_request(220, 150)\n'
    '        self._panda_event.set_margin_end(10)\n'
    '        self._panda_event.set_margin_bottom(30)\n'
    '        self._panda_event.connect("button-press-event", self._open_chat)\n'
    '        overlay.add_overlay(self._panda_event)'
)

# Remove old positioning from DrawingArea since EventBox handles it
content = content.replace(
    '        self._panda_da.set_halign(Gtk.Align.END)\n'
    '        self._panda_da.set_valign(Gtk.Align.END)\n'
    '        self._panda_da.set_margin_end(10)\n'
    '        self._panda_da.set_margin_bottom(30)',
    ''
)

# 2. Add chat window and methods
CHAT_CODE = '''
    def _open_chat(self, widget, event):
        """Open AquaGPT chat interface."""
        if hasattr(self, '_chat_window') and self._chat_window and self._chat_window.get_visible():
            self._chat_window.present()
            return

        self._chat_window = Gtk.Window(title="AquaGPT")
        self._chat_window.set_default_size(500, 400)
        self._chat_window.set_transient_for(self)
        self._chat_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.25, 0.55, 1))
        header.set_size_request(-1, 45)

        # Logo in header
        logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"
        if os.path.exists(logo_path):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 30, 30, True)
            logo_img = Gtk.Image.new_from_pixbuf(pb)
            logo_img.set_margin_start(10)
            header.pack_start(logo_img, False, False, 0)

        title = Gtk.Label(label="AquaGPT")
        title.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        title.modify_font(Pango.FontDescription("Sans bold 16"))
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(label="Your Water Assistant")
        subtitle.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.7, 0.85, 1, 0.8))
        subtitle.modify_font(Pango.FontDescription("Sans 10"))
        header.pack_start(subtitle, False, False, 0)

        close_btn = Gtk.Button(label="\u2715")
        close_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 0.5, 0.5, 1))
        close_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0, 0, 0, 0))
        close_btn.modify_font(Pango.FontDescription("Sans bold 14"))
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b: self._chat_window.hide())
        header.pack_end(close_btn, False, False, 5)

        main_box.pack_start(header, False, False, 0)

        # Chat messages area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.96, 0.97, 0.98, 1))

        self._chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._chat_box.set_margin_start(10)
        self._chat_box.set_margin_end(10)
        self._chat_box.set_margin_top(10)
        scroll.add(self._chat_box)
        main_box.pack_start(scroll, True, True, 0)

        # Welcome message
        self._add_bot_message("Hi! I am AquaGPT, your water assistant. Ask me anything!")

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_box.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        input_box.set_margin_start(8)
        input_box.set_margin_end(8)
        input_box.set_margin_top(6)
        input_box.set_margin_bottom(8)

        self._chat_entry = Gtk.Entry()
        self._chat_entry.set_placeholder_text("Type your question...")
        self._chat_entry.modify_font(Pango.FontDescription("Sans 13"))
        self._chat_entry.connect("activate", self._send_chat)
        input_box.pack_start(self._chat_entry, True, True, 0)

        send_btn = Gtk.Button(label="Send")
        send_btn.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.4, 0.75, 1))
        send_btn.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        send_btn.modify_font(Pango.FontDescription("Sans bold 12"))
        send_btn.connect("clicked", self._send_chat)
        input_box.pack_start(send_btn, False, False, 0)

        main_box.pack_start(input_box, False, False, 0)

        self._chat_window.add(main_box)
        self._chat_window.show_all()

    def _add_bot_message(self, text):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)

        # Bot avatar
        avatar = Gtk.Label(label="\U0001F4A7")
        avatar.modify_font(Pango.FontDescription("Sans 16"))
        msg_box.pack_start(avatar, False, False, 0)

        # Message bubble
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_max_width_chars(45)
        label.set_halign(Gtk.Align.START)
        label.modify_font(Pango.FontDescription("Noto Sans 12"))
        label.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.15, 0.3, 1))
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        msg_box.pack_start(label, False, False, 0)

        self._chat_box.pack_start(msg_box, False, False, 0)
        msg_box.show_all()
        # Scroll to bottom
        GLib.idle_add(self._scroll_chat_bottom)

    def _add_user_message(self, text):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)

        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_max_width_chars(40)
        label.set_halign(Gtk.Align.END)
        label.modify_font(Pango.FontDescription("Noto Sans 12"))
        label.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.4, 0.75, 1))
        label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        msg_box.pack_end(label, False, False, 0)

        self._chat_box.pack_start(msg_box, False, False, 0)
        msg_box.show_all()
        GLib.idle_add(self._scroll_chat_bottom)

    def _scroll_chat_bottom(self):
        adj = self._chat_box.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())
        return False

    def _send_chat(self, widget):
        text = self._chat_entry.get_text().strip()
        if not text:
            return
        self._add_user_message(text)
        self._chat_entry.set_text("")

        # Get answer in background
        def get_answer():
            answer = self._get_ai_answer(text)
            GLib.idle_add(self._add_bot_message, answer)
        threading.Thread(target=get_answer, daemon=True).start()

    def _get_ai_answer(self, question):
        """Get answer using DuckDuckGo Instant Answer API."""
        try:
            q = question.lower()

            # Water-related built-in answers
            water_qa = {
                "what is water": "Water (H2O) is a transparent, tasteless, odorless substance that is essential for all known forms of life.",
                "save water": "Tips to save water: Fix leaks, use low-flow fixtures, collect rainwater, reuse greywater, and water plants in early morning.",
                "water quality": "Water quality is measured by pH, turbidity, dissolved oxygen, TDS, and presence of contaminants like bacteria or heavy metals.",
                "what is tds": "TDS (Total Dissolved Solids) measures the total amount of dissolved substances in water. Safe drinking water should have TDS below 500 mg/L.",
                "what is ph": "pH measures how acidic or basic water is on a scale of 0-14. Pure water has a pH of 7. Drinking water should be between 6.5-8.5.",
                "water positive": "Water positive means replenishing more water than you consume. Fluxgen helps organizations achieve water positivity through smart monitoring.",
                "what is aquabox": "AquaBox is a water monitoring and alert system by Fluxgen Sustainable Technologies. It monitors water levels, flow rates, and sends real-time alerts.",
                "what is fluxgen": "Fluxgen Sustainable Technologies builds IoT solutions for water management, helping organizations become water-positive.",
                "who are you": "I am AquaGPT, your AI water assistant by Fluxgen Sustainable Technologies. I help monitor water usage and answer water-related questions.",
                "hello": "Hello! I am AquaGPT. How can I help you with water management today?",
                "hi": "Hi there! I am AquaGPT, your water assistant. Ask me anything about water!",
            }

            for key, answer in water_qa.items():
                if key in q:
                    return answer

            # Try DuckDuckGo API
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": question, "format": "json", "no_html": "1"},
                timeout=10
            )
            data = resp.json()

            # Check for instant answer
            if data.get("AbstractText"):
                return data["AbstractText"][:300]
            if data.get("Answer"):
                return data["Answer"]
            if data.get("Definition"):
                return data["Definition"]
            if data.get("RelatedTopics") and len(data["RelatedTopics"]) > 0:
                topic = data["RelatedTopics"][0]
                if isinstance(topic, dict) and topic.get("Text"):
                    return topic["Text"][:300]

            return "I am still learning! For now, I can answer water-related questions. Try asking about water quality, TDS, pH, or water saving tips."

        except Exception as e:
            return "Sorry, I could not find an answer right now. Please try again later."

'''

content = content.replace(
    '    def _scroll_to_section(self, section):',
    CHAT_CODE + '    def _scroll_to_section(self, section):'
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

ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
ssh.exec_command('killall aplay 2>/dev/null')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
