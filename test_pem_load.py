import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64

# Try to load from a PEM file directly
try:
    with open('kalshi_private.pem', 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None
        )
    print("✓ Successfully loaded private key from PEM file")
    
    # Test signing
    timestamp = str(int(1640995200 * 1000))  # Sample timestamp
    message = timestamp + "GET" + "/trade-api/v2/markets/test/orderbook"
    
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    
    b64_sig = base64.b64encode(signature).decode('utf-8')
    print(f"✓ Generated signature: {b64_sig[:50]}...")
    
except FileNotFoundError:
    print("✗ kalshi_private.pem file not found")
except Exception as e:
    print(f"✗ Error loading PEM file: {e}")
