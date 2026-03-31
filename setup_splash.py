import paramiko, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.103', username='aquabox', password='aquabox@2026', timeout=10)

# 1. Create custom Plymouth theme directory
ssh.exec_command('echo "aquabox@2026" | sudo -S mkdir -p /usr/share/plymouth/themes/aquabox')
time.sleep(1)

# 2. Upload Fluxgen logo
sftp = ssh.open_sftp()
sftp.put(r'c:\Users\Anil Fluxgen\OneDrive\Desktop\Fluxgen-Logo.png', '/tmp/Fluxgen-Logo.png')
sftp.close()
ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/Fluxgen-Logo.png /usr/share/plymouth/themes/aquabox/')
time.sleep(1)

# 3. Create the splash screen script
SPLASH_SCRIPT = '''
Window.SetBackgroundTopColor(1.0, 1.0, 1.0);
Window.SetBackgroundBottomColor(0.95, 0.97, 1.0);

# Load logo
logo.image = Image("Fluxgen-Logo.png");
logo.sprite = Sprite(logo.image);
logo.sprite.SetX(Window.GetWidth() / 2 - logo.image.GetWidth() / 2);
logo.sprite.SetY(Window.GetHeight() / 2 - 80);

# Welcome text
welcome.image = Image.Text("Welcome to AquaBox", 0.07, 0.15, 0.35, "Sans Bold 18");
welcome.sprite = Sprite(welcome.image);
welcome.sprite.SetX(Window.GetWidth() / 2 - welcome.image.GetWidth() / 2);
welcome.sprite.SetY(Window.GetHeight() / 2 + 30);

# Powered by text
powered.image = Image.Text("Powered by Fluxgen", 0.35, 0.42, 0.52, "Sans 12");
powered.sprite = Sprite(powered.image);
powered.sprite.SetX(Window.GetWidth() / 2 - powered.image.GetWidth() / 2);
powered.sprite.SetY(Window.GetHeight() / 2 + 60);

# Tagline
tagline.image = Image.Text("Build a Water-Positive Future", 0.3, 0.55, 0.8, "Sans Italic 10");
tagline.sprite = Sprite(tagline.image);
tagline.sprite.SetX(Window.GetWidth() / 2 - tagline.image.GetWidth() / 2);
tagline.sprite.SetY(Window.GetHeight() / 2 + 85);

# Progress dots animation
dots_count = 0;
fun refresh_callback()
{
    dots_count++;
    dot_text = "";
    for (i = 0; i < (dots_count / 10) % 4; i++)
        dot_text += ".";

    loading.image = Image.Text("Loading" + dot_text, 0.5, 0.55, 0.65, "Sans 11");
    loading.sprite = Sprite(loading.image);
    loading.sprite.SetX(Window.GetWidth() / 2 - loading.image.GetWidth() / 2);
    loading.sprite.SetY(Window.GetHeight() / 2 + 115);
}
Plymouth.SetRefreshFunction(refresh_callback);
'''

sftp2 = ssh.open_sftp()
with sftp2.file('/tmp/aquabox.script', 'w') as f:
    f.write(SPLASH_SCRIPT)
sftp2.close()
ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/aquabox.script /usr/share/plymouth/themes/aquabox/')
time.sleep(1)

# 4. Create theme descriptor
THEME_DESC = '''[Plymouth Theme]
Name=AquaBox
Description=AquaBox boot splash - Fluxgen Sustainable Technologies
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/aquabox
ScriptFile=/usr/share/plymouth/themes/aquabox/aquabox.script
'''

sftp3 = ssh.open_sftp()
with sftp3.file('/tmp/aquabox.plymouth', 'w') as f:
    f.write(THEME_DESC)
sftp3.close()
ssh.exec_command('echo "aquabox@2026" | sudo -S cp /tmp/aquabox.plymouth /usr/share/plymouth/themes/aquabox/')
time.sleep(1)

# 5. Set as default theme
cmds = [
    'echo "aquabox@2026" | sudo -S plymouth-set-default-theme aquabox',
    'echo "aquabox@2026" | sudo -S update-initramfs -u',
]
for cmd in cmds:
    print('Running:', cmd[:50])
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    time.sleep(5)
    out = stdout.read().decode('utf-8', errors='replace')
    if out.strip():
        print(out[-200:])

# Verify
stdin, stdout, stderr = ssh.exec_command('plymouth-set-default-theme')
print('Current theme:', stdout.read().decode('utf-8', errors='replace').strip())

# List theme files
stdin, stdout, stderr = ssh.exec_command('ls -la /usr/share/plymouth/themes/aquabox/')
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print('Done! Reboot to see the new splash screen.')
