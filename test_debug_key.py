import os
from bot.adapters.kalshi import KalshiAdapter

# Create adapter with the key from .env
from dotenv import load_dotenv
load_dotenv('.env')

# Get the key
key = os.getenv('KALSHI_PRIVATE_KEY')
print(f"Key from .env: {key[:50] if key else 'None'}")
print(f"Starts with BEGIN: {key.startswith('-----BEGIN') if key else 'None'}")

# Create adapter
adapter = KalshiAdapter(
    kalshi_access_key=os.getenv('KALSHI_ACCESS_KEY'),
    kalshi_private_key=key
)

# Try to generate a signature
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
    
    # Try loading from PEM file
    pem_file = os.path.join(os.getcwd(), 'kalshi_private.pem')
    print(f"\nTrying PEM file: {pem_file}")
    if os.path.exists(pem_file):
        with open(pem_file, 'r') as f:
            pem_key = f.read()
        print(f"PEM key starts with: {pem_key[:50]}")
        
        # Create new adapter with PEM key
        adapter2 = KalshiAdapter(
            kalshi_access_key=os.getenv('KALSHI_ACCESS_KEY'),
            kalshi_private_key=pem_key
        )
        try:
            sig2 = adapter2._generate_signature("123", "GET", "/test")
            print(f"✓ PEM signature generated: {sig2[:50]}")
        except Exception as e2:
            print(f"✗ PEM error: {e2}")
