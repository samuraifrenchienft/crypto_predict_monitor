import os
from bot.adapters.kalshi import KalshiAdapter

# Create a new PEM file with the working key
key = "MIIEogIBAAKCAQEA+laawbVft544HxmAoQ3ibmnmH1BH5uEYU7fvEGxDzT3x2kwanxErJAhjAMTEwYh2PxX5Hssjp3nGrszYiMedFyoyVoZBNMqQBaxGAMe9uU/rmIvRcnh0ovdWM+W8gvL8oLFXNM8jeXTfEZNuljo2AjvJVxHaIpHVJlaT2axO3yFqONxQqMGvbhsRyf7X52jZJDuYPazIzB3hUAAQNpMtrqRBSq2I2kRc8kqc3A1n5v9Nf2V5nRSMVNxOEn1zkC5pXL4zYt+WPacfxZg31H1VMyEUsjn0lMSmorK5efZAPnKn9C4jdvdVhmdnaBTXHv7xyUdG3nS2sJoJGhr0pa+KTbiwIDAQABAoIBAGz0vK6KrnpQlsSSaPWwAVllJg+C9Yh7eAcYCyjutiPiTh1g+lVs50fOVfgTHKfXjfe7GqGp6IA0oTKC4ScvLaUWwxlqoO7liuh62XziZPaQQRH9oTgRBc7lvwJbgo4eNezEHj1eDLCTuxG3SvKUqXku4eiv540ni5PeiDomBjPrZy49Fh2XiARh3blC7zyn7IufCv76PsHsDDw3ZpNzTSdbhGnKt/aZQiHQiaLNjvqfD1/BBsVJj3UD1rpkWPW96mWyvdZMe1Lblzd+Y5cDEVkqah8RRzQNby1S2gBFrQBR6b3/T7Li2mJkiKJ03ikGm8lhYegpBlZRzoDlyOSo2ECgYEA6zIxlLwrPfQ1nyrIJyCbVBA3X4B2dv2DLND3NdaIVMtxOTSLjcvqf6K7qTRVWzSw0uiRnxN0ITiMmYIppwISVLo6eFWPo3i15lKZ2sY2a7wL2/R+u01UjwJXBIOtR4cEt1sOv4f9DpgdwB4pI/Srteo4FptgEndXPN2mqdVGDcCgYEA/qPwmbVgqJKUUjCqw8MeL8Tz83PCZDgpFzNv5d2M6d98ECiDMNS0uaUrhvRUvR51C2ya5gjh/hAtgolpsH/AtRHFBaU1e2EpYNAPkMliImDW0OLEanK7/Io4SExswLQcSfjOeEp7hdOAcxcyUiKWFYuJyWYu3W77zorHtlIhU0CgYB6JiJMH3UwfhaeA2QLL+sdoxXYao/7bQa+o0MMrHjSM8zDA0v/okk/Ir1yIjRLUAeCVd5XltmGRiv3VXVh2VMP9ahEOXmMXAXmX+S7yD6qQoYd1ILFj00K66QQliXnrBrTYaa7yWjL7FAzWKqUNYGNOeEEWVPkRyGLg31381gQKBgE9AXMiqD7xHaowuA2fMGWAKr1ZM5pjJD7JToE/M/UyDh3FThdrjBffVS26a4k0qn70vTzs9NEq3c8rz04UZLi2IBjCs2OD+Ondt4p7cuR6OUFn4nOy49kUd7Hgv1Q2ejt3iWMc41biXa70QEAZ7ZYlCKw69kkKm6N++h6ux4hdAoGAJ8oU8mZTS5xih3V4PCfyt9ZK+YC83VWm25v0WyjBSYuECmes1aEL95eOOre4fjdhr31BfpHhUiI6/8gHVsCNhA2mLpWBrNDjbdQgd9isY+hgpNBWinL0c7ZPqEkxg9hWkGWTekaHWTpKO7XSTbftlt8kgw4HvCPwyaOM9fl4b0="

# Add padding if needed
if len(key) % 4 != 0:
    key += '=' * (4 - (len(key) % 4))

# Create properly formatted PEM
formatted_key = "-----BEGIN RSA PRIVATE KEY-----\n"
for i in range(0, len(key), 64):
    formatted_key += key[i:i+64] + "\n"
formatted_key += "-----END RSA PRIVATE KEY-----"

# Write to file
with open('kalshi_private.pem', 'w') as f:
    f.write(formatted_key)

print("Created new PEM file with padding")

# Test it
adapter = KalshiAdapter(
    kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
    kalshi_private_key=None
)

try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
