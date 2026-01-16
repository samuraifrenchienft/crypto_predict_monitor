import os
from dotenv import load_dotenv
load_dotenv('.env')

print("=== Kalshi Configuration ===")
print(f"Access Key: {os.environ.get('KALSHI_ACCESS_KEY', 'Not set')}")
print(f"Private Key: {'Set' if os.environ.get('KALSHI_PRIVATE_KEY') else 'Not set'}")

# Check if keys look like demo/production
access_key = os.environ.get('KALSHI_ACCESS_KEY', '')
if access_key:
    print(f"\nAccess key analysis:")
    print(f"  Length: {len(access_key)}")
    print(f"  Format: {'UUID-like' if '-' in access_key else 'Other'}")
    
# Test with a simple request
import requests
import time
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Load the PEM key
with open('kalshi_private.pem', 'r') as f:
    private_key_pem = f.read()

private_key = serialization.load_pem_private_key(
    private_key_pem.encode('utf-8'),
    password=None
)

# Try the public endpoint without auth
print("\n=== Testing Public Endpoint ===")
response = requests.get("https://api.elections.kalshi.com/trade-api/v2/series")
print(f"Public series status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Series count: {len(data.get('series', []))}")

# Try authenticated endpoint
timestamp = str(int(time.time() * 1000))
path = "/trade-api/v2/markets"
message = timestamp + "GET" + path

signature = private_key.sign(
    message.encode('utf-8'),
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.DIGEST_LENGTH
    ),
    hashes.SHA256()
)
signature_b64 = base64.b64encode(signature).decode('utf-8')

headers = {
    "KALSHI-ACCESS-KEY": access_key,
    "KALSHI-ACCESS-SIGNATURE": signature_b64,
    "KALSHI-ACCESS-TIMESTAMP": timestamp
}

print("\n=== Testing Authenticated Endpoint ===")
response = requests.get("https://api.elections.kalshi.com/trade-api/v2/markets?limit=1", headers=headers)
print(f"Markets status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    markets = data.get('markets', [])
    print(f"Markets found: {len(markets)}")
    if markets:
        m = markets[0]
        print(f"Sample market: {m.get('ticker')}")
        print(f"Has yes_price: {m.get('yes_price') is not None}")
        print(f"Status: {m.get('status')}")
else:
    print(f"Error: {response.text[:200]}")
