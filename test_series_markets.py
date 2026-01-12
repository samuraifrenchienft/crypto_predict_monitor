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

# Get markets from a specific series
series_ticker = "KXAFRICALEADEROUT"  # African politics
timestamp = str(int(time.time() * 1000))
path = f"/trade-api/v2/series/{series_ticker}/markets"
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

response = requests.get(f"https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}/markets", headers=headers)
print(f"Series markets status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    markets = data.get('markets', [])
    print(f"Found {len(markets)} markets in series")
    
    # Check each market for prices
    for m in markets[:5]:
        print(f"\nMarket: {m.get('ticker')}")
        print(f"Title: {m.get('title')}")
        print(f"Status: {m.get('status')}")
        print(f"Close time: {m.get('close_time')}")
        
        if m.get('yes_price') is not None:
            print(f"YES price: ${m.get('yes_price')}")
            print(f"NO price: ${m.get('no_price')}")
            
            # Check orderbook
            market_ticker = m['ticker']
            timestamp = str(int(time.time() * 1000))
            path = f"/trade-api/v2/markets/{market_ticker}/orderbook"
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
            
            orderbook_response = requests.get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{market_ticker}/orderbook", headers=headers)
            if orderbook_response.status_code == 200:
                orderbook_data = orderbook_response.json()
                orderbook = orderbook_data.get("orderbook", {})
                if orderbook.get("yes") or orderbook.get("no"):
                    print(f"✓ ORDERBOOK FOUND!")
                    print(f"  Yes: {orderbook.get('yes', [])[:2]}")
                    print(f"  No: {orderbook.get('no', [])[:2]}")
                else:
                    print(f"  No orderbook (null)")
        else:
            print(f"No price data")
else:
    print(f"Error: {response.text}")
