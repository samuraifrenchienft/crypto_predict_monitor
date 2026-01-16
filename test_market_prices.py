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

# Get markets
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

# Get all markets
response = requests.get("https://api.elections.kalshi.com/trade-api/v2/markets", headers=headers)
data = response.json()
markets = data.get('markets', [])

print(f"Found {len(markets)} markets")

# Look for markets with prices
markets_with_prices = []
for m in markets[:20]:  # Check first 20
    if m.get('yes_price') is not None and m.get('no_price') is not None:
        markets_with_prices.append(m)
        print(f"\nMarket: {m['ticker']}")
        print(f"Title: {m.get('title', 'N/A')}")
        print(f"YES price: ${m.get('yes_price', 0)}")
        print(f"NO price: ${m.get('no_price', 0)}")
        
        # Check orderbook for this market
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
                print(f"✓ Has orderbook data!")
                print(f"  Yes levels: {orderbook.get('yes')}")
                print(f"  No levels: {orderbook.get('no')}")
                break
            else:
                print(f"  No orderbook data")
        
        if len(markets_with_prices) >= 5:
            break

if not markets_with_prices:
    print("\nNo markets with prices found in first 20")
