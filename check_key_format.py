import os
from dotenv import load_dotenv
load_dotenv(".env.txt")

# Try both env variable names
key = os.getenv("KALSHI_PRIVATE_KEY") or os.getenv("env:KALSHI_PRIVATE_KEY")
print(f"Key type: {type(key)}")
print(f"Key length: {len(key) if key else 'None'}")
print(f"First 100 chars: {key[:100] if key else 'None'}")
print(f"Starts with -----BEGIN: {key.startswith('-----BEGIN') if key else 'None'}")

# Try to detect format
if key:
    if key.startswith('-----BEGIN'):
        print("Format: PEM")
    elif all(c in '0123456789ABCDEFabcdef' for c in key):
        print("Format: Hex")
    else:
        try:
            import base64
            base64.b64decode(key)
            print("Format: Base64")
        except:
            print("Format: Unknown (might need special handling)")
