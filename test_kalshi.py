import requests
import time
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
ACCESS_KEY = os.getenv('KALSHI_ACCESS_KEY')
PRIVATE_KEY_PEM = os.getenv('KALSHI_PRIVATE_KEY')

print("ACCESS_KEY:", ACCESS_KEY)
print("PRIVATE_KEY loaded:", "YES" if PRIVATE_KEY_PEM else "NO")

# Load private key
try:
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PEM.encode(),
        password=None
    )
    print("Private key loaded successfully")
except Exception as e:
    print("Error loading private key:", e)
    exit()

# Create signature
timestamp = str(int(time.time()))
method = 'GET'
path = '/markets'
message = timestamp + method + path

print("Message to sign:", message)

signature = private_key.sign(
    message.encode(),
    padding.PKCS1v15(),
    hashes.SHA256()
).hex()

print("Signature created successfully")

# Make request
url = "https://api.elections.kalshi.com/trade-api/v2/markets"
headers = {
    "KALSHI-ACCESS-KEY": ACCESS_KEY,
    "KALSHI-ACCESS-TIMESTAMP": timestamp,
    "KALSHI-ACCESS-SIGNATURE": signature
}

print("Making request to:", url)
response = requests.get(url, headers=headers)
print("Response status:", response.status_code)
print("Response:", response.text)