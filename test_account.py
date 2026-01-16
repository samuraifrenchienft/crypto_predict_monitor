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

# Check account balance and positions
timestamp = str(int(time.time() * 1000))
path = "/trade-api/v2/portfolio"
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
    "KALSHI-ACCESS-KEY": "7462d858-3aa1-4cda-936e-48551efcf81f",
    "KALSHI-ACCESS-SIGNATURE": signature_b64,
    "KALSHI-ACCESS-TIMESTAMP": timestamp
}

try:
    response = requests.get("https://api.elections.kalshi.com/trade-api/v2/portfolio", headers=headers)
    print(f"Portfolio status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Balance: ${data.get('balance', 0)}")
    else:
        print(f"Portfolio error: {response.text}")
except Exception as e:
    print(f"Portfolio error: {e}")

# Check if we're in demo mode
timestamp = str(int(time.time() * 1000))
path = "/trade-api/v2/user"
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
    "KALSHI-ACCESS-KEY": "7462d858-3aa1-4cda-936e-48551efcf81f",
    "KALSHI-ACCESS-SIGNATURE": signature_b64,
    "KALSHI-ACCESS-TIMESTAMP": timestamp
}

try:
    response = requests.get("https://api.elections.kalshi.com/trade-api/v2/user", headers=headers)
    print(f"\nUser status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"User email: {data.get('email', 'N/A')}")
        print(f"Demo mode: {data.get('demo', 'Unknown')}")
    else:
        print(f"User error: {response.text}")
except Exception as e:
    print(f"User error: {e}")

# Check series endpoints to see available markets
timestamp = str(int(time.time() * 1000))
path = "/trade-api/v2/series"
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
    "KALSHI-ACCESS-KEY": "7462d858-3aa1-4cda-936e-48551efcf81f",
    "KALSHI-ACCESS-SIGNATURE": signature_b64,
    "KALSHI-ACCESS-TIMESTAMP": timestamp
}

try:
    response = requests.get("https://api.elections.kalshi.com/trade-api/v2/series", headers=headers)
    print(f"\nSeries status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        series = data.get('series', [])
        print(f"Found {len(series)} series")
        for s in series[:5]:
            print(f"  - {s.get('ticker', 'N/A')}: {s.get('title', 'N/A')}")
    else:
        print(f"Series error: {response.text}")
except Exception as e:
    print(f"Series error: {e}")
