import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('.env')

from bot.adapters.kalshi import KalshiAdapter

# Create adapter with debug
class DebugKalshiAdapter(KalshiAdapter):
    def _generate_signature(self, timestamp: str, method: str, path: str) -> str:
        import os
        import re
        
        print(f"Initial key type: {type(self.kalshi_private_key)}")
        print(f"Initial key starts with BEGIN: {self.kalshi_private_key.startswith('-----BEGIN') if self.kalshi_private_key else 'None'}")
        
        # Try to load from PEM file if string key doesn't work
        if isinstance(self.kalshi_private_key, str) and not self.kalshi_private_key.startswith('-----BEGIN'):
            print("Key doesn't start with BEGIN, trying to load from file...")
            
            # Try loading from file in project root
            pem_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'kalshi_private.pem')
            print(f"Looking for PEM at: {pem_file}")
            print(f"PEM exists: {os.path.exists(pem_file)}")
            
            if os.path.exists(pem_file):
                with open(pem_file, 'r') as f:
                    self.kalshi_private_key = f.read()
                print(f"Loaded from PEM, starts with: {self.kalshi_private_key[:50]}")
            else:
                # Try to extract from .env.txt
                env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env.txt')
                print(f"Looking for .env.txt at: {env_file}")
                print(f".env.txt exists: {os.path.exists(env_file)}")
                
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        content = f.read()
                    match = re.search(r'-----BEGIN RSA PRIVATE KEY-----([^"]+)-----END RSA PRIVATE KEY-----', content, re.DOTALL)
                    if match:
                        # Clean up the key - remove \n and extra spaces
                        key = match.group(1).replace('\\n', '').replace(' ', '')
                        # Add proper line breaks every 64 characters
                        formatted_key = "-----BEGIN RSA PRIVATE KEY-----\n"
                        for i in range(0, len(key), 64):
                            formatted_key += key[i:i+64] + "\n"
                        formatted_key += "-----END RSA PRIVATE KEY-----"
                        self.kalshi_private_key = formatted_key
                        print(f"Loaded from .env.txt, starts with: {self.kalshi_private_key[:50]}")
        
        # Now call the parent method
        return super()._generate_signature(timestamp, method, path)

# Create debug adapter
adapter = DebugKalshiAdapter(
    kalshi_access_key=os.getenv('KALSHI_ACCESS_KEY'),
    kalshi_private_key=os.getenv('KALSHI_PRIVATE_KEY')
)

# Try to generate a signature
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
