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

# Test a specific market
market_ticker = "KXMVESPORTSMULTIGAMEEXTENDED-S2025285383DB96A-C063559B22B"
timestamp = str(int(time.time() * 1000))
path = f"/trade-api/v2/markets/{market_ticker}/orderbook"
message = timestamp + "GET" + path

# Generate signature
signature = private_key.sign(
    message.encode('utf-8'),
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.DIGEST_LENGTH
    ),
    hashes.SHA256()
)
signature_b64 = base64.b64encode(signature).decode('utf-8')

# Make request
headers = {
    "KALSHI-ACCESS-KEY": "7462d858-3aa1-4cda-936e-48551efcf81f",
    "KALSHI-ACCESS-SIGNATURE": signature_b64,
    "KALSHI-ACCESS-TIMESTAMP": timestamp
}

url = f"https://api.elections.kalshi.com/trade-api/v2/markets/{market_ticker}/orderbook"
response = requests.get(url, headers=headers)

print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}...")

if response.status_code == 200:
    data = response.json()
    orderbook = data.get("orderbook", {})
    yes_levels = orderbook.get("yes", [])
    no_levels = orderbook.get("no", [])
    print(f"\nYes levels: {yes_levels[:2]}")
    print(f"No levels: {no_levels[:2]}")
