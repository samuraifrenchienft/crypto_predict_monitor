import os
from bot.adapters.kalshi import KalshiAdapter

# Extract from .env.txt
with open('.env.txt', 'r') as f:
    content = f.read()

# Find the key
import re
match = re.search(r'KALSHI_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----([^"]+)-----END RSA PRIVATE KEY-----"', content, re.DOTALL)
if match:
    key_part = match.group(1)
    # Remove literal \n and spaces
    key_clean = key_part.replace('\\n', '').replace(' ', '').replace('\n', '')
    
    # Create proper PEM format
    formatted_key = "-----BEGIN RSA PRIVATE KEY-----\n"
    for i in range(0, len(key_clean), 64):
        formatted_key += key_clean[i:i+64] + "\n"
    formatted_key += "-----END RSA PRIVATE KEY-----"
    
    # Save to PEM file
    with open('kalshi_private.pem', 'w') as f:
        f.write(formatted_key)
    
    print("Created PEM from .env.txt")
    
    # Test with adapter
    adapter = KalshiAdapter(
        kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
        kalshi_private_key=None  # Force loading from file
    )
    
    try:
        sig = adapter._generate_signature("123", "GET", "/test")
        print(f"✓ Signature generated: {sig[:50]}")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("Could not extract key")
