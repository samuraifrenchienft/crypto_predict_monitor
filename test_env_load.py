from dotenv import load_dotenv
load_dotenv('.env')

import os
print(f"Access key from os.getenv: {os.getenv('KALSHI_ACCESS_KEY')}")
print(f"Access key from os.environ: {os.environ.get('KALSHI_ACCESS_KEY')}")

# Check all env vars
print("\nAll KALSHI env vars:")
for k, v in os.environ.items():
    if 'KALSHI' in k:
        print(f"{k}: {v[:50] if v else 'None'}")
