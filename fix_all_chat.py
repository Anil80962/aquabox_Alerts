import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

# Find _add_bot_message (line 1776) and replace through the end
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'def _add_bot_message(self' in line:
        start_line = i
    if start_line and i > start_line and line.strip().startswith('def ') and 'bot_message' not in line:
        end_line = i
        break

print(f"Found: lines {start_line+1} to {end_line+1}")

NEW_BOT = '''    def _add_bot_message(self, text, speak=False):
        msg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        msg_box.set_margin_top(4)
        msg_box.set_margin_start(5)

        # Bot avatar - Fluxgen icon
        icon_path = "/home/aquabox/Desktop/Aquabox/fluxgen-icon.jpg"
        if os.path.exists(icon_path):
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 24, 24, True)
            avatar = Gtk.Image.new_from_pixbuf(pb)
        else:
            avatar = Gtk.Label(label="B")
        msg_box.pack_start(avatar, False, False, 0)

        # Bubble
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
        try:
            adj = self._chat_box.get_parent().get_vadjustment()
            adj.set_value(adj.get_upper())
        except: pass

        # Typing animation
        self._chat_typing_text = text
        self._chat_typing_idx = 0
        self._chat_typing_label = label
        GLib.timeout_add(25, self._chat_type_tick)

        # Speak answer
        if speak and text:
            def do_speak():
                try:
                    import subprocess
                    from gtts import gTTS
                    if TTS_LANG != "en":
                        tts = gTTS(text=text, lang=TTS_LANG)
                    else:
                        tts = gTTS(text=text, lang="en", tld="co.in")
                    tts.save("/tmp/aquabox_chat.mp3")
                    subprocess.run(["ffmpeg", "-y", "-i", "/tmp/aquabox_chat.mp3", "-ar", "44100", "/tmp/aquabox_chat.wav"], capture_output=True, timeout=15)
                    subprocess.run(["aplay", "-D", "plughw:0,0", "-q", "/tmp/aquabox_chat.wav"], capture_output=True, timeout=30)
                except Exception as e:
                    print("[AquaBox Chat] Speak error: " + str(e))
            threading.Thread(target=do_speak, daemon=True).start()

    def _chat_type_tick(self):
        if self._chat_typing_idx <= len(self._chat_typing_text):
            self._chat_typing_label.set_text(self._chat_typing_text[:self._chat_typing_idx])
            self._chat_typing_idx += 1
            try:
                adj = self._chat_box.get_parent().get_vadjustment()
                adj.set_value(adj.get_upper())
            except: pass
            return True
        return False

'''

new_lines = NEW_BOT.split('\n')
lines[start_line:end_line] = new_lines

# Also fix the water drop icon in the mascot overlay
content = '\n'.join(lines)

# Replace aquagpt-logo.png with water drop logi.png for the mascot
content = content.replace(
    'logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"',
    'logo_path = "/home/aquabox/Desktop/Aquabox/aquagpt-logo.png"'
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

# Also upload the water drop logo as the mascot icon
sftp2 = ssh.open_sftp()
sftp2.put(r'c:\Users\Anil Fluxgen\Downloads\water drop logi.png', '/home/aquabox/Desktop/Aquabox/aquagpt-logo.png')
sftp2.close()

# Verify
check = 'import py_compile\ntry:\n    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)\n    print("SYNTAX OK")\nexcept py_compile.PyCompileError as e:\n    print("ERROR:", str(e))\n'
sftp3 = ssh.open_sftp()
with sftp3.file('/tmp/check.py', 'w') as f:
    f.write(check)
sftp3.close()
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
