import os
import sys
sys.path.insert(0, '.')

# Use environment variables directly
from bot.adapters.kalshi import KalshiAdapter

# Get the actual values from os.environ
access_key = os.environ.get('KALSHI_ACCESS_KEY')
private_key = os.environ.get('KALSHI_PRIVATE_KEY')

print(f"Access Key from environ: {access_key}")
print(f"Private Key from environ starts with: {private_key[:50] if private_key else 'None'}")

# Create adapter with env vars
adapter = KalshiAdapter(
    kalshi_access_key=access_key,
    kalshi_private_key=private_key
)

print(f"Adapter Access Key: {adapter.kalshi_access_key}")
print(f"Adapter Private Key starts with PEM: {adapter.kalshi_private_key.startswith('-----BEGIN') if adapter.kalshi_private_key else 'None'}")

# Try to generate a signature
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
