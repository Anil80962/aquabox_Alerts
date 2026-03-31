import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
content = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode()

# 1. Make stat boxes clickable - wrap in EventBox
# Replace _make_stat to return clickable box
old_make_stat = '''    def _make_stat(self, num, label, css_class):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("stat-box")
        num_label = Gtk.Label(label=num)
        num_label.get_style_context().add_class("stat-num")
        num_label.get_style_context().add_class(css_class)
        text_label = Gtk.Label(label=label)
        text_label.get_style_context().add_class("stat-label")
        box.pack_start(num_label, False, False, 0)
        box.pack_start(text_label, False, False, 0)'''

new_make_stat = '''    def _make_stat(self, num, label, css_class):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("stat-box")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        num_label = Gtk.Label(label=num)
        num_label.get_style_context().add_class("stat-num")
        num_label.get_style_context().add_class(css_class)
        text_label = Gtk.Label(label=label)
        text_label.get_style_context().add_class("stat-label")
        box.pack_start(num_label, False, False, 0)
        box.pack_start(text_label, False, False, 0)
        btn.add(box)'''

content = content.replace(old_make_stat, new_make_stat)

# Fix the return to return (btn, num_label)
content = content.replace(
    '        return (box, num_label)',
    '        return (btn, num_label)'
)

# 2. Connect click handlers to each stat box
old_stats = '''        self.stats_box.pack_start(self.stat_unread[0], True, True, 0)
        self.stats_box.pack_start(self.stat_read[0], True, True, 0)
        self.stats_box.pack_start(self.stat_total[0], True, True, 0)
        self.stats_box.pack_start(self.stat_offline[0], True, True, 0)'''

new_stats = '''        self.stat_unread[0].connect("clicked", lambda b: self._scroll_to_section("unread"))
        self.stat_read[0].connect("clicked", lambda b: self._scroll_to_section("read"))
        self.stat_total[0].connect("clicked", lambda b: self._scroll_to_section("top"))
        self.stat_offline[0].connect("clicked", lambda b: self._scroll_to_section("offline"))
        self.stats_box.pack_start(self.stat_unread[0], True, True, 0)
        self.stats_box.pack_start(self.stat_read[0], True, True, 0)
        self.stats_box.pack_start(self.stat_total[0], True, True, 0)
        self.stats_box.pack_start(self.stat_offline[0], True, True, 0)'''

content = content.replace(old_stats, new_stats)

# 3. Add section markers and scroll method
# Add marker labels when rendering sections
content = content.replace(
    '            unread_header = Gtk.Label(label=f"\\u25CF  UNREAD ({len(unread_alerts)})")',
    '            self._section_unread = Gtk.Label(label="")\n'
    '            self._section_unread.set_size_request(-1, 0)\n'
    '            self.alerts_container.pack_start(self._section_unread, False, False, 0)\n'
    '            unread_header = Gtk.Label(label=f"\\u25CF  UNREAD ({len(unread_alerts)})")'
)

content = content.replace(
    '            read_header = Gtk.Label(label=f"\\u25CF  READ ({len(read_alerts)})")',
    '            self._section_read = Gtk.Label(label="")\n'
    '            self._section_read.set_size_request(-1, 0)\n'
    '            self.alerts_container.pack_start(self._section_read, False, False, 0)\n'
    '            read_header = Gtk.Label(label=f"\\u25CF  READ ({len(read_alerts)})")'
)

# Add offline marker
content = content.replace(
    '        self._all_offline_alerts = offline_list\n        if offline_list:',
    '        self._all_offline_alerts = offline_list\n'
    '        self._section_offline = Gtk.Label(label="")\n'
    '        self._section_offline.set_size_request(-1, 0)\n'
    '        self.alerts_container.pack_start(self._section_offline, False, False, 0)\n'
    '        if offline_list:'
)

# 4. Add the scroll method
SCROLL_METHOD = '''    def _scroll_to_section(self, section):
        """Scroll alerts list to a specific section."""
        target = None
        if section == "unread" and hasattr(self, '_section_unread'):
            target = self._section_unread
        elif section == "read" and hasattr(self, '_section_read'):
            target = self._section_read
        elif section == "offline" and hasattr(self, '_section_offline'):
            target = self._section_offline
        elif section == "top":
            # Scroll to top
            adj = self.alerts_container.get_parent().get_vadjustment()
            adj.set_value(0)
            return

        if target:
            def do_scroll():
                alloc = target.get_allocation()
                adj = self.alerts_container.get_parent().get_vadjustment()
                adj.set_value(alloc.y)
            GLib.idle_add(do_scroll)

'''

content = content.replace(
    '    def _update_counters(self, delta):',
    SCROLL_METHOD + '    def _update_counters(self, delta):'
)

with sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
    f.write(content)
sftp.close()

ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl stop aquabox-alerts.service')
time.sleep(1)
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
