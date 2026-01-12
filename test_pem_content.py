import os

# Read the PEM file
with open('kalshi_private.pem', 'r') as f:
    content = f.read()

print(f"Content starts with: {repr(content[:50])}")
print(f"Has BEGIN: {content.startswith('-----BEGIN')}")
print(f"First line: {repr(content.split(chr(10))[0])}")  # chr(10) is \n

# Check for BOM
if content.startswith('\ufeff'):
    print("Has BOM")
else:
    print("No BOM")
