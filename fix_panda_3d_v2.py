import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()
lines = sftp.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

# Replace lines 1602-1737 (Panda body to cr.restore)
NEW_PANDA = """        # 3D Panda with gradients, shadows, highlights
        px = w * 0.7
        py = h - 38
        bounce = _math.sin(self._panda_phase * 2) * 2
        cr.save()
        cr.translate(px, py + bounce)
        sc = 1.1

        # Shadow
        cr.save()
        cr.set_source_rgba(0, 0, 0, a * 0.15)
        cr.scale(1.2, 0.3)
        cr.arc(0, 35, 20 * sc, 0, _math.pi * 2)
        cr.fill()
        cr.restore()

        # Body - 3D gradient sphere
        pat = cairo.RadialGradient(-5 * sc, -12 * sc, 2, 0, -5 * sc, 25 * sc)
        pat.add_color_stop_rgba(0, 1, 1, 1, a)
        pat.add_color_stop_rgba(0.6, 0.95, 0.95, 0.97, a)
        pat.add_color_stop_rgba(1, 0.82, 0.82, 0.85, a)
        cr.set_source(pat)
        cr.save()
        cr.scale(1, 1.25)
        cr.arc(0, -6 * sc, 22 * sc, 0, _math.pi * 2)
        cr.restore()
        cr.fill()

        # Body outline
        cr.set_source_rgba(0.7, 0.7, 0.72, a * 0.3)
        cr.set_line_width(0.8)
        cr.save()
        cr.scale(1, 1.25)
        cr.arc(0, -6 * sc, 22 * sc, 0, _math.pi * 2)
        cr.restore()
        cr.stroke()

        # Head - 3D gradient
        pat2 = cairo.RadialGradient(-4 * sc, -42 * sc, 2, 0, -38 * sc, 22 * sc)
        pat2.add_color_stop_rgba(0, 1, 1, 1, a)
        pat2.add_color_stop_rgba(0.5, 0.96, 0.96, 0.98, a)
        pat2.add_color_stop_rgba(1, 0.84, 0.84, 0.87, a)
        cr.set_source(pat2)
        cr.arc(0, -38 * sc, 21 * sc, 0, _math.pi * 2)
        cr.fill()
        cr.set_source_rgba(0.7, 0.7, 0.72, a * 0.3)
        cr.set_line_width(0.8)
        cr.arc(0, -38 * sc, 21 * sc, 0, _math.pi * 2)
        cr.stroke()

        # Ears - 3D gradient
        for ex in [-16, 16]:
            pat_e = cairo.RadialGradient(ex * sc - 2, -54 * sc - 1, 1, ex * sc, -54 * sc, 9 * sc)
            pat_e.add_color_stop_rgba(0, 0.25, 0.25, 0.28, a)
            pat_e.add_color_stop_rgba(1, 0.05, 0.05, 0.08, a)
            cr.set_source(pat_e)
            cr.arc(ex * sc, -54 * sc, 9 * sc, 0, _math.pi * 2)
            cr.fill()
            cr.set_source_rgba(0.55, 0.35, 0.4, a * 0.5)
            cr.arc(ex * sc, -54 * sc, 5 * sc, 0, _math.pi * 2)
            cr.fill()

        # Eye patches - 3D
        for ex in [-8, 8]:
            pat_p = cairo.RadialGradient(ex * sc - 1, -41 * sc, 1, ex * sc, -40 * sc, 8 * sc)
            pat_p.add_color_stop_rgba(0, 0.2, 0.2, 0.22, a)
            pat_p.add_color_stop_rgba(1, 0.02, 0.02, 0.05, a)
            cr.set_source(pat_p)
            cr.save()
            cr.translate(ex * sc, -40 * sc)
            cr.scale(1.1, 0.85)
            cr.arc(0, 0, 8 * sc, 0, _math.pi * 2)
            cr.restore()
            cr.fill()

        # Eyes - glossy 3D
        blink = abs(_math.sin(self._panda_phase * 0.5))
        eye_h = max(0.3, blink)
        for ex in [-8, 8]:
            cr.set_source_rgba(1, 1, 1, a)
            cr.save()
            cr.translate(ex * sc, -40 * sc)
            cr.scale(1, eye_h)
            cr.arc(0, 0, 4 * sc, 0, _math.pi * 2)
            cr.restore()
            cr.fill()
            pat_i = cairo.RadialGradient(ex * sc + 0.5, -40.5 * sc, 0.5, ex * sc, -40 * sc, 3 * sc)
            pat_i.add_color_stop_rgba(0, 0.15, 0.12, 0.3, a)
            pat_i.add_color_stop_rgba(1, 0.02, 0.02, 0.1, a)
            cr.set_source(pat_i)
            cr.save()
            cr.translate(ex * sc + (1 if ex > 0 else -1), -40 * sc)
            cr.scale(1, eye_h)
            cr.arc(0, 0, 2.5 * sc, 0, _math.pi * 2)
            cr.restore()
            cr.fill()
            cr.set_source_rgba(1, 1, 1, a * 0.9)
            cr.arc(ex * sc - 1, -41.5 * sc, 1.2 * sc, 0, _math.pi * 2)
            cr.fill()

        # Nose - 3D
        pat_n = cairo.RadialGradient(-0.5 * sc, -33.5 * sc, 0.5, 0, -33 * sc, 4 * sc)
        pat_n.add_color_stop_rgba(0, 0.3, 0.3, 0.32, a)
        pat_n.add_color_stop_rgba(1, 0.08, 0.08, 0.1, a)
        cr.set_source(pat_n)
        cr.save()
        cr.translate(0, -33 * sc)
        cr.scale(1.3, 0.8)
        cr.arc(0, 0, 3.5 * sc, 0, _math.pi * 2)
        cr.restore()
        cr.fill()
        cr.set_source_rgba(0.5, 0.5, 0.55, a * 0.5)
        cr.arc(-1 * sc, -34 * sc, 1.2 * sc, 0, _math.pi * 2)
        cr.fill()

        # Mouth
        cr.set_source_rgba(0.12, 0.12, 0.15, a)
        cr.set_line_width(1.3)
        cr.move_to(-4 * sc, -30 * sc)
        cr.curve_to(-2 * sc, -27 * sc, 2 * sc, -27 * sc, 4 * sc, -30 * sc)
        cr.stroke()

        # Cheeks
        cr.set_source_rgba(1, 0.6, 0.65, a * 0.25)
        cr.arc(-13 * sc, -35 * sc, 4 * sc, 0, _math.pi * 2)
        cr.fill()
        cr.arc(13 * sc, -35 * sc, 4 * sc, 0, _math.pi * 2)
        cr.fill()

        # Arms - 3D
        wave = _math.sin(self._panda_phase * 3) * 0.3
        for side, rot in [(-1, -0.4 + wave), (1, 0.4 - wave * 2)]:
            cr.save()
            cr.translate(side * 21 * sc, -10 * sc)
            cr.rotate(rot)
            pat_a = cairo.RadialGradient(-1, -2, 1, 0, 0, 6 * sc)
            pat_a.add_color_stop_rgba(0, 0.2, 0.2, 0.22, a)
            pat_a.add_color_stop_rgba(1, 0.05, 0.05, 0.08, a)
            cr.set_source(pat_a)
            cr.save()
            cr.scale(1, 2.8)
            cr.arc(0, 0, 5.5 * sc, 0, _math.pi * 2)
            cr.restore()
            cr.fill()
            cr.restore()

        # Legs - 3D
        for lx in [-10, 10]:
            pat_l = cairo.RadialGradient(lx * sc - 1, 14 * sc, 1, lx * sc, 15 * sc, 8 * sc)
            pat_l.add_color_stop_rgba(0, 0.2, 0.2, 0.22, a)
            pat_l.add_color_stop_rgba(1, 0.05, 0.05, 0.08, a)
            cr.set_source(pat_l)
            cr.save()
            cr.translate(lx * sc, 15 * sc)
            cr.scale(1, 0.7)
            cr.arc(0, 0, 8 * sc, 0, _math.pi * 2)
            cr.restore()
            cr.fill()

        # Water drop - glossy 3D
        pat_d = cairo.RadialGradient(-1 * sc, -13 * sc, 1, 0, -10 * sc, 8 * sc)
        pat_d.add_color_stop_rgba(0, 0.4, 0.7, 1, a * 0.8)
        pat_d.add_color_stop_rgba(0.5, 0.2, 0.5, 0.9, a * 0.6)
        pat_d.add_color_stop_rgba(1, 0.1, 0.3, 0.7, a * 0.3)
        cr.set_source(pat_d)
        s = 7 * sc
        cr.move_to(0, -16 * sc)
        cr.curve_to(s * 0.5, -9 * sc, s * 0.7, -3 * sc, 0, 1 * sc)
        cr.curve_to(-s * 0.7, -3 * sc, -s * 0.5, -9 * sc, 0, -16 * sc)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, a * 0.5)
        cr.arc(-2 * sc, -12 * sc, 2 * sc, 0, _math.pi * 2)
        cr.fill()

        cr.restore()"""

new_lines = NEW_PANDA.split('\n')

# Replace lines 1602 to 1737
lines[1602:1737] = new_lines

content = '\n'.join(lines)

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
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()
print('Done!')
