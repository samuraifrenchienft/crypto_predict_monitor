import os
from dotenv import load_dotenv
load_dotenv('.env.txt')

# Try to get the key
key = os.getenv('KALSHI_PRIVATE_KEY')
print(f'Key length: {len(key) if key else "None"}')
print(f'Starts with PEM: {key.startswith("-----BEGIN") if key else "None"}')
print(f'Ends with PEM: {key.endswith("-----END RSA PRIVATE KEY-----") if key else "None"}')
