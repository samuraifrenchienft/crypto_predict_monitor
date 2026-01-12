import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env')

from bot.adapters.kalshi import KalshiAdapter

# Create adapter
adapter = KalshiAdapter(
    kalshi_access_key=os.getenv('KALSHI_ACCESS_KEY'),
    kalshi_private_key=os.getenv('KALSHI_PRIVATE_KEY')
)

# Check what the adapter has
print(f"Adapter key type: {type(adapter.kalshi_private_key)}")
print(f"Adapter key starts with BEGIN: {adapter.kalshi_private_key.startswith('-----BEGIN') if adapter.kalshi_private_key else 'None'}")
if adapter.kalshi_private_key:
    print(f"First 50 chars: {adapter.kalshi_private_key[:50]}")

# Try to generate a signature
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
    
    # Try to trigger the file loading
    print("\nTrying to load from file...")
    try:
        sig2 = adapter._generate_signature("456", "GET", "/test2")
        print(f"✓ Signature after file load: {sig2[:50]}")
    except Exception as e2:
        print(f"✗ Still error: {e2}")
