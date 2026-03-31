import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

sftp = ssh.open_sftp()

# Find ALL syntax errors
check = '''
import py_compile
try:
    py_compile.compile("/home/aquabox/Desktop/Aquabox/aquabox_alerts.py", doraise=True)
    print("SYNTAX OK")
except py_compile.PyCompileError as e:
    print("ERROR:", str(e))
'''
with sftp.file('/tmp/check.py', 'w') as f:
    f.write(check)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/check.py 2>&1')
result = stdout.read().decode('utf-8', errors='replace').strip()
print(result)

if 'ERROR' in result:
    # Extract line number
    import re
    m = re.search(r'line (\d+)', result)
    if m:
        line_num = int(m.group(1))
        print(f"\nError at line {line_num}")

        sftp2 = ssh.open_sftp()
        lines = sftp2.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'r').read().decode().split('\n')

        # Show context
        for j in range(max(0, line_num-5), min(len(lines), line_num+5)):
            marker = ">>>" if j == line_num-1 else "   "
            print(f"{marker} {j+1}: [{lines[j]}]")

        # Fix: find lines with "if _announce_stop: break" that are at wrong indent
        fixed = False
        for i in range(len(lines)):
            s = lines[i]
            # Check for mismatched indent after "if _announce_stop: break"
            if 'if _announce_stop: break' in s:
                # Get this line's indent
                indent = len(s) - len(s.lstrip())
                # Check next line's indent
                if i+1 < len(lines):
                    next_indent = len(lines[i+1]) - len(lines[i+1].lstrip())
                    if next_indent > indent and 'tts = gTTS' in lines[i+1]:
                        # Next line should be at same indent
                        spaces = ' ' * indent
                        lines[i+1] = spaces + lines[i+1].lstrip()
                        print(f"Fixed line {i+2}")
                        fixed = True
                    # Check line after that
                    if i+2 < len(lines):
                        next2_indent = len(lines[i+2]) - len(lines[i+2].lstrip())
                        if next2_indent > indent and 'tts.save' in lines[i+2]:
                            lines[i+2] = spaces + lines[i+2].lstrip()
                            print(f"Fixed line {i+3}")
                            fixed = True
                    if i+3 < len(lines):
                        if 'subprocess.run' in lines[i+3] and 'ffmpeg' in lines[i+3]:
                            lines[i+3] = spaces + lines[i+3].lstrip()
                            print(f"Fixed line {i+4}")
                            fixed = True

        if fixed:
            content = '\n'.join(lines)
            with sftp2.file('/home/aquabox/Desktop/Aquabox/aquabox_alerts.py', 'w') as f:
                f.write(content)
            print("File saved")

            # Check again
            stdin2, stdout2, stderr2 = ssh.exec_command('python3 /tmp/check.py 2>&1')
            print("After fix:", stdout2.read().decode('utf-8', errors='replace').strip())

        sftp2.close()

# Restart
ssh.exec_command('echo "aquabox@2026" | sudo -S pkill -9 -f aquabox_alerts.py')
time.sleep(2)
ssh.exec_command('echo "aquabox@2026" | sudo -S systemctl start aquabox-alerts.service')
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active aquabox-alerts.service')
print('Service:', stdout.read().decode('utf-8', errors='replace').strip())

ssh.close()
print('Done!')
