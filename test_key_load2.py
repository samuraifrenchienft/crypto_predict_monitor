import os
from dotenv import load_dotenv
load_dotenv('.env.txt')

# Helper to get env vars (handles PowerShell format)
def get_env(key: str):
    # Try standard env var first
    value = os.getenv(key)
    if value:
        return value.strip().strip('"').strip("'")
    
    # Try PowerShell format (remove $env: and quotes)
    ps_key = key.replace("KALSHI_", "env:KALSHI_")
    value = os.getenv(ps_key)
    if value:
        return value.strip().strip('"').strip("'")
    
    return None

# Try to get the key
key = get_env("KALSHI_PRIVATE_KEY")
print(f'Key length: {len(key) if key else "None"}')
print(f'Starts with PEM: {key.startswith("-----BEGIN") if key else "None"}')
print(f'Ends with PEM: {key.endswith("-----END RSA PRIVATE KEY-----") if key else "None"}')
if key and len(key) > 100:
    print(f'First 100 chars: {key[:100]}')
    print(f'Last 100 chars: {key[-100:]}')
