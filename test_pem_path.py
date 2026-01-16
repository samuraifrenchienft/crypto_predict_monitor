import os
print(f"Current dir: {os.getcwd()}")
print(f"Looking for: {os.path.join(os.getcwd(), 'kalshi_private.pem')}")
print(f"File exists: {os.path.exists('kalshi_private.pem')}")

if os.path.exists('kalshi_private.pem'):
    with open('kalshi_private.pem', 'r') as f:
        content = f.read()
    print(f"File content starts with: {content[:50]}")
    print(f"File content length: {len(content)}")
