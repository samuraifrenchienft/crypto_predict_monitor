# ============================================================================
# LIVE API Configuration - NO DEMO DATA
# ============================================================================

# POLYMARKET - LIVE endpoints
POLYMARKET_CONFIG = {
    'url': 'https://clob.polymarket.com',
    'ws_url': 'wss://clob.polymarket.com/ws',
    'price_endpoint': '/price',
    'markets_endpoint': '/markets',
    'is_dev': False,  # CRITICAL: Must be False for LIVE data
}

# MANIFOLD - LIVE endpoints  
MANIFOLD_CONFIG = {
    'url': 'https://api.manifold.markets/v0',
    'markets_endpoint': '/markets',
    'bets_endpoint': '/bets',
    'is_dev': False,  # CRITICAL: Must be False for LIVE data
}

# LIMITLESS - LIVE endpoints
LIMITLESS_CONFIG = {
    'url': 'https://api.limitless.exchange',
    'markets_endpoint': '/markets',
    'is_dev': False,  # CRITICAL: Must be False for LIVE data
}

# AZURO - LIVE GraphQL endpoints
AZURO_CONFIG = {
    'endpoints': {
        'polygon': 'https://thegraph.onchainfeed.org/subgraphs/name/azuro-protocol/azuro-api-polygon-v3',
        'gnosis': 'https://thegraph.onchainfeed.org/subgraphs/name/azuro-protocol/azuro-api-gnosis-v3',
        'base': 'https://thegraph.onchainfeed.org/subgraphs/name/azuro-protocol/azuro-api-base-v3',
        'chiliz': 'https://thegraph.onchainfeed.org/subgraphs/name/azuro-protocol/azuro-api-chiliz-v3',
    },
    'is_dev': False,  # CRITICAL: Must be False for LIVE data
}

# COINBASE - LIVE price data
COINBASE_CONFIG = {
    'url': 'https://api.exchange.coinbase.com',
    'products_endpoint': '/products',
    'candles_endpoint': '/candles',
    'is_dev': False,  # CRITICAL: Must be False for LIVE data
}

# LIVE API configuration object
LIVE_API_CONFIG = {
    'polymarket': POLYMARKET_CONFIG,
    'manifold': MANIFOLD_CONFIG,
    'limitless': LIMITLESS_CONFIG,
    'azuro': AZURO_CONFIG,
    'coinbase': COINBASE_CONFIG,
}

# CRITICAL: Demo mode flags - ALL MUST BE FALSE
DEMO_MODE = False
USE_MOCK_DATA = False
IS_DEV_MODE = False

# LIVE data validation
def validate_live_data(data):
    """Verify data is real, not demo/mock"""
    if not data:
        return False, "No data provided"
    
    # Check for demo indicators
    demo_indicators = [
        'demo', 'mock', 'test', 'example',
        '0x0000000000000000000000000000000000000000',  # Zero address
        'localhost', '127.0.0.1', '0.0.0.0'
    ]
    
    data_str = str(data).lower()
    for indicator in demo_indicators:
        if indicator in data_str:
            return False, f"Demo data detected: {indicator}"
    
    # Check for realistic market data
    if isinstance(data, dict):
        # Check prices aren't all 0.5 (demo pattern)
        if 'prices' in data:
            prices = data['prices']
            if all(p == 0.5 for p in prices if isinstance(p, (int, float))):
                return False, "All prices are 0.5 - demo data detected"
        
        # Check for real volumes
        if 'volume' in data and data['volume'] == 0:
            return False, "Zero volume - demo data detected"
        
        # Check for real timestamps
        if 'timestamp' in data:
            try:
                import datetime
                ts = data['timestamp']
                if isinstance(ts, str):
                    dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    # Check if timestamp is recent (within last 24 hours)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    if (now - dt).days > 1:
                        return False, "Old timestamp - demo data detected"
            except:
                pass
    
    return True, "Live data validated"

# Export for use in other modules
__all__ = [
    'LIVE_API_CONFIG',
    'DEMO_MODE',
    'USE_MOCK_DATA', 
    'IS_DEV_MODE',
    'validate_live_data'
]
