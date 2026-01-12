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

# Hardcode the access key
access_key = "7462d858-3aa1-4cda-936e-48551efcf81f"

# Test different market statuses
timestamp = str(int(time.time() * 1000))
path = "/trade-api/v2/markets?status=closed&limit=5"
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

print("=== Testing Closed Markets ===")
response = requests.get("https://api.elections.kalshi.com/trade-api/v2/markets?status=closed&limit=5", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    markets = data.get('markets', [])
    print(f"Found {len(markets)} closed markets")
    for m in markets[:2]:
        print(f"\nMarket: {m.get('ticker')}")
        print(f"Title: {m.get('title')}")
        print(f"Status: {m.get('status')}")
        print(f"Settled: {m.get('settled')}")
        if m.get('yes_price') is not None:
            print(f"Final YES price: ${m.get('yes_price')}")

# Test settled markets
timestamp = str(int(time.time() * 1000))
path = "/trade-api/v2/markets?status=settled&limit=5"
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

print("\n=== Testing Settled Markets ===")
response = requests.get("https://api.elections.kalshi.com/trade-api/v2/markets?status=settled&limit=5", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    markets = data.get('markets', [])
    print(f"Found {len(markets)} settled markets")
    for m in markets[:2]:
        print(f"\nMarket: {m.get('ticker')}")
        print(f"Title: {m.get('title')}")
        print(f"Status: {m.get('status')}")
        print(f"Settled: {m.get('settled')}")
        print(f"Yes price: ${m.get('yes_price', 'N/A')}")
        print(f"No price: ${m.get('no_price', 'N/A')}")
