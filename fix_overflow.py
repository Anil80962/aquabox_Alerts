import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Fix login page - reduce logo size and margins to fit 480px
content = content.replace(
    'pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 320, 100, True)',
    'pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 220, 65, True)'
)

# Reduce logo margin
content = content.replace(
    '            logo.set_margin_top(20)\n            card.pack_start(logo',
    '            logo.set_margin_top(8)\n            card.pack_start(logo'
)

# Reduce tagline margin
content = content.replace(
    '        tag.set_margin_bottom(4)\n        card.pack_start(tag',
    '        tag.set_margin_bottom(2)\n        card.pack_start(tag'
)

# Reduce divider margins
content = content.replace(
    '        div.set_margin_top(10)\n        div.set_margin_bottom(8)',
    '        div.set_margin_top(4)\n        div.set_margin_bottom(4)'
)

# Reduce Sign In font
content = content.replace(
    'signin.modify_font(Pango.FontDescription("Sans bold 13"))',
    'signin.modify_font(Pango.FontDescription("Sans bold 11"))'
)

# Reduce username/password label margins
content = content.replace(
    '        ulabel.set_margin_top(8)',
    '        ulabel.set_margin_top(4)'
)
content = content.replace(
    '        plabel.set_margin_top(6)',
    '        plabel.set_margin_top(3)'
)

# Reduce keyboard and admin button margins
content = content.replace(
    '        kb_btn.set_margin_top(6)\n        kb_btn.set_margin_bottom(18)',
    '        kb_btn.set_margin_top(3)\n        kb_btn.set_margin_bottom(4)'
)
content = content.replace(
    '        admin_btn.set_margin_bottom(10)',
    '        admin_btn.set_margin_bottom(6)'
)

# Reduce card width
content = content.replace(
    '        card.set_size_request(420, -1)',
    '        card.set_size_request(360, -1)'
)

# Reduce login button margin
content = content.replace(
    '        btn.set_margin_top(6)',
    '        btn.set_margin_top(3)'
)

# 2. Fix admin settings dialog - make it scrollable and fit 800x480
content = content.replace(
    '        dialog = Gtk.Dialog(title="Admin Settings", parent=self, flags=0)\n        dialog.set_default_size(400, 350)',
    '        dialog = Gtk.Dialog(title="Admin Settings", parent=self, flags=0)\n        dialog.set_default_size(400, 420)\n'
    '        # Make scrollable\n'
    '        scroll_admin = Gtk.ScrolledWindow()\n'
    '        scroll_admin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)'
)

# Wrap admin content in scroll
content = content.replace(
    '        box = dialog.get_content_area()\n        box.set_spacing(8)',
    '        outer_box = dialog.get_content_area()\n'
    '        scroll_admin = Gtk.ScrolledWindow()\n'
    '        scroll_admin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)\n'
    '        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)\n'
    '        scroll_admin.add(box)\n'
    '        outer_box.pack_start(scroll_admin, True, True, 0)'
)

# Reduce admin dialog margins
content = content.replace(
    '        box.set_margin_start(20)\n        box.set_margin_end(20)\n        box.set_margin_top(10)',
    '        box.set_margin_start(15)\n        box.set_margin_end(15)\n        box.set_margin_top(5)'
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
