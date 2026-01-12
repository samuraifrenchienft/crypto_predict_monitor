import os
from bot.adapters.kalshi import KalshiAdapter

# Use the working key directly (from our earlier successful test)
key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAAKCAQEA+laawbVft544HxmAoQ3ibmnmH1BH5uEYU7fvEGxDzT3x2kwa\nnxErJAhjAMTEwYh2PxX5Hssjp3nGrszYiMedFyoyVoZBNMqQBaxGAMe9uU/rmIvRc\nh0ovdWM+W8gvL8oLFXNM8jeXTfEZNuljo2AjvJVxHaIpHVJlaT2axO3yFqONxQqMG\nvbhsRyf7X52jZJDuYPazIzB3hUAAQNpMtrqRBSq2I2kRc8kqc3A1n5v9Nf2V5nRS\nMVNxOEn1zkC5pXL4zYt+WPacfxZg31H1VMyEUsjn0lMSmorK5efZAPnKn9C4jdvdV\nhmdnaBTXHv7xyUdG3nS2sJoJGhr0pa+KTbiwIDAQABAoIBAGz0vK6KrnpQlsSSaP\nWwAVllJg+C9Yh7eAcYCyjutiPiTh1g+lVs50fOVfgTHKfXjfe7GqGp6IA0oTKC4S\ncvLaUWwxlqoO7liuh62XziZPaQQRH9oTgRBc7lvwJbgo4eNezEHj1eDLCTuxG3SvK\nUqXku4eiv540ni5PeiDomBjPrZy49Fh2XiARh3blC7zyn7IufCv76PsHsDDw3ZpNz\nTSdbhGnKt/aZQiHQiaLNjvqfD1/BBsVJj3UD1rpkWPW96mWyvdZMe1Lblzd+Y5cD\nEVkqah8RRzQNby1S2gBFrQBR6b3/T7Li2mJkiKJ03ikGm8lhYegpBlZRzoDlyOSo\n2ECgYEA6zIxlLwrPfQ1nyrIJyCbVBA3X4B2dv2DLND3NdaIVMtxOTSLjcvqf6K7qT\nRVWzSw0uiRnxN0ITiMmYIppwISVLo6eFWPo3i15lKZ2sY2a7wL2/R+u01UjwJXBIO\ntR4cEt1sOv4f9DpgdwB4pI/Srteo4FptgEndXPN2mqdVGDcCgYEA/qPwmbVgqJKUUj\nCqw8MeL8Tz83PCZDgpFzNv5d2M6d98ECiDMNS0uaUrhvRUvR51C2ya5gjh/hAtgol\npsH/AtRHFBaU1e2EpYNAPkMliImDW0OLEanK7/Io4SExswLQcSfjOeEp7hdOAcxcy\nUiKWFYuJyWYu3W77zorHtlIhU0CgYB6JiJMH3UwfhaeA2QLL+sdoxXYao/7bQa+o0\nMMrHjSM8zDA0v/okk/Ir1yIjRLUAeCVd5XltmGRiv3VXVh2VMP9ahEOXmMXAXmX+S\n7yD6qQoYd1ILFj00K66QQliXnrBrTYaa7yWjL7FAzWKqUNYGNOeEEWVPkRyGLg313\n81gQKBgE9AXMiqD7xHaowuA2fMGWAKr1ZM5pjJD7JToE/M/UyDh3FThdrjBffVS2\n6a4k0qn70vTzs9NEq3c8rz04UZLi2IBjCs2OD+Ondt4p7cuR6OUFn4nOy49kUd7Hg\nv1Q2ejt3iWMc41biXa70QEAZ7ZYlCKw69kkKm6N++h6ux4hdAoGAJ8oU8mZTS5xih3\nV4PCfyt9ZK+YC83VWm25v0WyjBSYuECmes1aEL95eOOre4fjdhr31BfpHhUiI6/8g\nHVsCNhA2mLpWBrNDjbdQgd9isY+hgpNBWinL0c7ZPqEkxg9hWkGWTekaHWTpKO7XS\nTbftlt8kgw4HvCPwyaOM9fl4b0=\n-----END RSA PRIVATE KEY-----"

# Create adapter with the key directly
adapter = KalshiAdapter(
    kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
    kalshi_private_key=key
)

print(f"Adapter Access Key: {adapter.kalshi_access_key}")
print(f"Private Key starts with PEM: {adapter.kalshi_private_key.startswith('-----BEGIN')}")

# Try to generate a signature
try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
