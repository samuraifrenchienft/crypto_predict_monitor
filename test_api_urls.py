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

# Try different base URLs
base_urls = [
    "https://api.elections.kalshi.com/trade-api/v2",
    "https://api.kalshi.com/trade-api/v2",
    "https://trading-api.kalshi.com/trade-api/v2"
]

for base_url in base_urls:
    print(f"\n=== Testing {base_url} ===")
    
    # Test exchange status
    timestamp = str(int(time.time() * 1000))
    path = "/trade-api/v2/exchange/status"
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
        response = requests.get(f"{base_url}/exchange/status", headers=headers, timeout=5)
        print(f"Exchange status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Active: {data.get('exchange_active')}")
            print(f"  Trading: {data.get('trading_active')}")
            
            # Try to get markets
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
                "KALSHI-ACCESS-KEY": "7462d858-3aa1-4cda-936e-48551efcf81f",
                "KALSHI-ACCESS-SIGNATURE": signature_b64,
                "KALSHI-ACCESS-TIMESTAMP": timestamp
            }
            
            markets_response = requests.get(f"{base_url}/markets", headers=headers, timeout=5)
            print(f"Markets: {markets_response.status_code}")
            if markets_response.status_code == 200:
                markets = markets_response.json().get('markets', [])
                print(f"  Found {len(markets)} markets")
                
                # Check first market for prices
                if markets:
                    m = markets[0]
                    if m.get('yes_price') is not None:
                        print(f"  First market has price: ${m.get('yes_price')}")
                    else:
                        print(f"  First market no price")
    except Exception as e:
        print(f"  Error: {e}")
