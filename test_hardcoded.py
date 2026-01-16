import os
import sys
sys.path.insert(0, '.')

from bot.adapters.kalshi import KalshiAdapter

# Create adapter with hardcoded values
adapter = KalshiAdapter(
    kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
    kalshi_private_key=None  # Force loading from file
)

print(f"Adapter Access Key: {adapter.kalshi_access_key}")

# Try to generate a signature - this should load from PEM file
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
    
    # Check if PEM file exists and is readable
    import os
    pem_file = 'kalshi_private.pem'
    if os.path.exists(pem_file):
        with open(pem_file, 'r') as f:
            content = f.read()
        print(f"PEM file exists, starts with: {content[:50]}")
        print(f"PEM file length: {len(content)}")
    else:
        print("PEM file does not exist")
