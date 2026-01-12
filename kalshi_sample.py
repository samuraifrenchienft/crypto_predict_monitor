import requests
import time
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# Load environment variables
load_dotenv('.env')

# Get credentials
ACCESS_KEY = os.getenv('KALSHI_ACCESS_KEY')
PRIVATE_KEY_FILE = os.getenv('KALSHI_PRIVATE_KEY_FILE')

# Check if credentials are available
if not ACCESS_KEY or not PRIVATE_KEY_FILE:
    print("⚠️  Kalshi credentials not configured. Set KALSHI_ACCESS_KEY and KALSHI_PRIVATE_KEY_FILE in .env")
    print("   Once configured, this script will connect to Kalshi API for market data and trading.")
    exit(0)

# Load private key from file
try:
    with open(PRIVATE_KEY_FILE, 'r') as f:
        PRIVATE_KEY_PEM = f.read()
except FileNotFoundError:
    print(f"❌ Kalshi private key file not found: {PRIVATE_KEY_FILE}")
    print("   Please ensure the file exists and contains your Kalshi private key.")
    exit(0)

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Load private key
try:
    # Try loading as PKCS#8 first
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PEM.encode(),
        password=None
    )
    print("✅ Kalshi private key loaded successfully")
except ValueError as e:
    print(f"❌ Kalshi private key error: {e}")
    print("   Please ensure your private key is in the correct PEM format.")
    exit(0)

def sign_request(method, path):
    """Generate RSA signature for Kalshi API request"""
    timestamp = str(int(time.time()))
    message = timestamp + method + path
    
    signature = private_key.sign(
        message.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    ).hex()
    
    return {
        'KALSHI-ACCESS-KEY': ACCESS_KEY,
        'KALSHI-ACCESS-TIMESTAMP': timestamp,
        'KALSHI-ACCESS-SIGNATURE': signature
    }

def query_market_data(search_term):
    """Query API for market data (search for NYC weather)"""
    path = '/markets'
    headers = sign_request('GET', path)
    
    url = BASE_URL + path
    params = {}  # No filter - get all markets
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        markets = response.json().get('markets', [])
        print(f"Found {len(markets)} NYC weather markets\n")
        
        if markets:
            market = markets[0]  # Get first market
            print(f"Market: {market['ticker']}")
            print(f"Question: {market.get('title', 'N/A')}")
            print(f"YES price: ${market.get('yes_price', 0)}")
            print(f"NO price: ${market.get('no_price', 0)}\n")
            return market
    else:
        print(f"Error querying markets: {response.status_code} - {response.text}\n")
    
    return None

def query_orderbook(market_ticker):
    """Query the orderbook for a specific market"""
    path = f'/markets/{market_ticker}/orderbook'
    headers = sign_request('GET', path)
    
    url = BASE_URL + path
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        orderbook = response.json()
        print(f"Orderbook for {market_ticker}:")
        
        if 'yes' in orderbook:
            yes_bids = orderbook['yes'].get('bids', [])
            yes_asks = orderbook['yes'].get('asks', [])
            print(f"  YES - Best Bid: ${yes_bids[0][0] if yes_bids else 'N/A'}, Best Ask: ${yes_asks[0][0] if yes_asks else 'N/A'}")
        
        if 'no' in orderbook:
            no_bids = orderbook['no'].get('bids', [])
            no_asks = orderbook['no'].get('asks', [])
            print(f"  NO  - Best Bid: ${no_bids[0][0] if no_bids else 'N/A'}, Best Ask: ${no_asks[0][0] if no_asks else 'N/A'}\n")
        
        return orderbook
    else:
        print(f"Error querying orderbook: {response.status_code} - {response.text}\n")
    
    return None

def place_order(market_ticker, side, price, quantity):
    """Place a limit order (1 unit)"""
    path = '/orders'
    headers = sign_request('POST', path)
    headers['Content-Type'] = 'application/json'
    
    url = BASE_URL + path
    
    payload = {
        'ticker': market_ticker,
        'side': side,  # 'yes' or 'no'
        'type': 'limit',
        'price': price,
        'count': quantity
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200 or response.status_code == 201:
        order = response.json()
        order_id = order.get('order_id')
        print(f"Order placed successfully!")
        print(f"Order ID: {order_id}")
        print(f"Side: {side}, Price: ${price}, Quantity: {quantity}\n")
        return order_id
    else:
        print(f"Error placing order: {response.status_code} - {response.text}\n")
    
    return None

def cancel_order(order_id):
    """Cancel an order"""
    path = f'/orders/{order_id}'
    headers = sign_request('DELETE', path)
    
    url = BASE_URL + path
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 200 or response.status_code == 204:
        print(f"Order {order_id} cancelled successfully!\n")
        return True
    else:
        print(f"Error cancelling order: {response.status_code} - {response.text}\n")
    
    return False

# MAIN EXECUTION
if __name__ == "__main__":
    print("=== Kalshi API Sample ===\n")
    
    # 1. Query market data for NYC weather
    print("1. Querying market data for NYC weather...")
    market = query_market_data('NYC_WEATHER')
    
    if market:
        market_ticker = market['ticker']
        
        # 2. Query orderbook for that market
        print("2. Querying orderbook...")
        orderbook = query_orderbook(market_ticker)
        
        # 3. Place an order (1 unit at a price)
        print("3. Placing order...")
        price = 0.50  # Limit price $0.50
        order_id = place_order(market_ticker, 'yes', price, 1)
        
        if order_id:
            # Wait a moment
            print("Waiting 2 seconds before cancelling...\n")
            time.sleep(2)
            
            # 4. Cancel the order
            print("4. Cancelling order...")
            cancel_order(order_id)
    else:
        print("No market found to trade")