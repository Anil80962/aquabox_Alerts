import paramiko, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('100.78.44.6', username='aquabox', password='aquabox@2026', timeout=10)

test_script = r'''
import requests, json
from datetime import datetime

# 1. Get token
print("=== Getting Token ===")
resp = requests.get(
    "https://prod-aquagen.azurewebsites.net/api/user/user/login?format=v1",
    headers={
        "accept": "application/json",
        "username": "sartorius",
        "password": "sartorius@1234",
        "LoginType": "DEFAULT"
    },
    timeout=15
)
print("Status:", resp.status_code)
data = resp.json()
token = data.get("token") or data.get("data", {}).get("token", "")
if "Bearer" in str(token):
    token = token.replace("Bearer ", "")
print("Token:", token[:60] + "..." if token else "NONE")

# 2. Get alerts
print("\n=== Getting Alerts ===")
today = datetime.now().strftime("%d/%m/%Y")
print("Date:", today)
resp2 = requests.get(
    f"https://prod-aquagen.azurewebsites.net/api/user/alerts?date={today}&type=daily",
    headers={
        "accept": "application/json",
        "authorization": f"Bearer {token}"
    },
    timeout=15
)
print("Status:", resp2.status_code)
alerts = resp2.json()
print("Type:", type(alerts).__name__)
if isinstance(alerts, dict):
    print("Keys:", list(alerts.keys()))
print("\nFull response:")
print(json.dumps(alerts, indent=2)[:2000])
'''

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_api.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_api.py 2>&1', timeout=30)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
