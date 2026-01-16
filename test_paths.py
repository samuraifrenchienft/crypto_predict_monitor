import os
from bot.adapters.kalshi import KalshiAdapter

# Check paths
adapter_file = os.path.dirname(os.path.abspath('bot/adapters/kalshi.py'))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath('bot/adapters/kalshi.py'))))
pem_file = os.path.join(project_root, 'kalshi_private.pem')
env_file = os.path.join(project_root, '.env.txt')

print(f"Adapter file dir: {adapter_file}")
print(f"Project root: {project_root}")
print(f"Looking for PEM at: {pem_file}")
print(f"PEM exists: {os.path.exists(pem_file)}")
print(f"Looking for .env.txt at: {env_file}")
print(f".env.txt exists: {os.path.exists(env_file)}")

if os.path.exists(pem_file):
    with open(pem_file, 'r') as f:
        content = f.read()
    print(f"PEM file starts with: {content[:50]}")
    bom = '\ufeff'
    print(f"PEM has BOM: {content.startswith(bom)}")
