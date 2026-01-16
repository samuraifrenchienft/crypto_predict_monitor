import os
from bot.adapters.kalshi import KalshiAdapter
import base64

# Load directly from .env.txt
with open('.env.txt', 'r') as f:
    content = f.read()
    
# Extract the key
import re
match = re.search(r'-----BEGIN RSA PRIVATE KEY-----([^"]+)-----END RSA PRIVATE KEY-----', content, re.DOTALL)
if match:
    # Clean up the key - remove \n and extra spaces
    key = match.group(1).replace('\\n', '').replace(' ', '')
    
    # Add proper line breaks every 64 characters
    formatted_key = "-----BEGIN RSA PRIVATE KEY-----\n"
    for i in range(0, len(key), 64):
        formatted_key += key[i:i+64] + "\n"
    formatted_key += "-----END RSA PRIVATE KEY-----"
    
    print(f"Key length: {len(key)}")
    print(f"First 50 chars: {key[:50]}")
    
    # Create adapter
    adapter = KalshiAdapter(
        kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
        kalshi_private_key=formatted_key
    )
    
    # Try to generate a signature
    try:
        sig = adapter._generate_signature("123", "GET", "/test")
        print(f"✓ Signature generated: {sig[:50]}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("Could not extract key from .env.txt")
