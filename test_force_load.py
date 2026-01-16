import os
from bot.adapters.kalshi import KalshiAdapter

# Create adapter with None key to force file loading
adapter = KalshiAdapter(
    kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
    kalshi_private_key=None
)

# Try to generate a signature - this should trigger file loading
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
    
    # Check what files exist
    current_dir = os.path.dirname(os.path.abspath('bot/adapters/kalshi.py'))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    pem_file = os.path.join(project_root, 'kalshi_private.pem')
    env_file = os.path.join(project_root, '.env.txt')
    
    print(f"\nCurrent dir: {current_dir}")
    print(f"Project root: {project_root}")
    print(f"PEM file: {pem_file}")
    print(f"PEM exists: {os.path.exists(pem_file)}")
    print(f".env.txt file: {env_file}")
    print(f".env.txt exists: {os.path.exists(env_file)}")
