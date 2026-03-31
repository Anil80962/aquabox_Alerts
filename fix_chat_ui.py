import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Replace _add_bot_message with rounded bubble + typing animation + TTS
old_bot = '''    def _add_bot_message(self, text):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)

        # Bot avatar
        avatar = Gtk.Label(label="\\U0001F4A7")
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
        GLib.idle_add(self._scroll_chat_bottom)'''

new_bot = '''    def _add_bot_message(self, text, speak=False):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)
        msg_box.set_margin_start(5)

        # Bot avatar - water drop image
        logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"
        if os.path.exists(logo_path):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 24, 24, True)
            avatar = Gtk.Image.new_from_pixbuf(pb)
        else:
            avatar = Gtk.Label(label="G")
        msg_box.pack_start(avatar, False, False, 0)

        # Message bubble with rounded background
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.93, 0.95, 0.98, 1))
        bubble.set_margin_end(40)

        label = Gtk.Label(label="")
        label.set_line_wrap(True)
        label.set_max_width_chars(50)
        label.set_halign(Gtk.Align.START)
        label.modify_font(Pango.FontDescription("Noto Sans 11"))
        label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.1, 0.15, 0.3, 1))
        label.set_margin_start(10)
        label.set_margin_end(10)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        bubble.pack_start(label, False, False, 0)
        msg_box.pack_start(bubble, True, True, 0)

        self._chat_box.pack_start(msg_box, False, False, 0)
        msg_box.show_all()
        GLib.idle_add(self._scroll_chat_bottom)

        # Typing animation for bot message
        self._chat_typing_text = text
        self._chat_typing_idx = 0
        self._chat_typing_label = label
        GLib.timeout_add(25, self._chat_typing_tick)

        # Speak the answer
        if speak and text:
            def speak_answer():
                try:
                    import subprocess
                    tts = gTTS(text=text, lang=TTS_LANG) if TTS_LANG != "en" else gTTS(text=text, lang="en", tld="co.in")
                    tts.save("/tmp/aquagpt_answer.mp3")
                    subprocess.run(["ffmpeg", "-y", "-i", "/tmp/aquagpt_answer.mp3", "-ar", "44100", "-ac", "1", "-filter:a", "volume=1.5,highpass=f=100,lowpass=f=8000", "/tmp/aquagpt_answer.wav"], capture_output=True, timeout=15)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", "/tmp/aquagpt_answer.wav"], capture_output=True, timeout=30)
                except Exception as e:
                    print("[" + now() + "] AquaGPT speak error: " + str(e))
            threading.Thread(target=speak_answer, daemon=True).start()

    def _chat_typing_tick(self):
        if self._chat_typing_idx <= len(self._chat_typing_text):
            self._chat_typing_label.set_text(self._chat_typing_text[:self._chat_typing_idx])
            self._chat_typing_idx += 1
            GLib.idle_add(self._scroll_chat_bottom)
            return True
        return False'''

content = content.replace(old_bot, new_bot)

# 2. Replace _add_user_message with rounded bubble
old_user = '''    def _add_user_message(self, text):
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
        GLib.idle_add(self._scroll_chat_bottom)'''

new_user = '''    def _add_user_message(self, text):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)
        msg_box.set_margin_end(5)

        # User bubble
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.08, 0.35, 0.7, 1))
        bubble.set_margin_start(80)

        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_max_width_chars(40)
        label.set_halign(Gtk.Align.END)
        label.modify_font(Pango.FontDescription("Noto Sans 11"))
        label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        label.set_margin_start(10)
        label.set_margin_end(10)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        bubble.pack_start(label, False, False, 0)

        msg_box.pack_end(bubble, True, True, 0)
        self._chat_box.pack_start(msg_box, False, False, 0)
        msg_box.show_all()
        GLib.idle_add(self._scroll_chat_bottom)'''

content = content.replace(old_user, new_user)

# 3. Update _send_chat to pass speak=True for answers
content = content.replace(
    '            answer = self._get_ai_answer(text)\n            GLib.idle_add(self._add_bot_message, answer)',
    '            answer = self._get_ai_answer(text)\n            GLib.idle_add(self._add_bot_message, answer, True)'
)

# 4. Add gTTS import at top of _get_ai_answer if not there
content = content.replace(
    '    def _get_ai_answer(self, question):',
    '    def _get_ai_answer(self, question):\n'
    '        from gtts import gTTS'
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
