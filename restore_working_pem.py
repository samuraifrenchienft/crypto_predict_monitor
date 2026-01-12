import os
from bot.adapters.kalshi import KalshiAdapter

# Use the exact working key from test_direct_key3.py
key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAAKCAQEA+laawbVft544HxmAoQ3ibmnmH1BH5uEYU7fvEGxDzT3x2kw\nanxErJAhjAMTEwYh2PxX5Hssjp3nGrszYiMedFyoyVoZBNMqQBaxGAMe9uU/rmIvR\nh0ovdWM+W8gvL8oLFXNM8jeXTfEZNuljo2AjvJVxHaIpHVJlaT2axO3yFqONxQqM\nGvbhsRyf7X52jZJDuYPazIzB3hUAAQNpMtrqRBSq2I2kRc8kqc3A1n5v9Nf2V5nRS\nMVNxOEn1zkC5pXL4zYt+WPacfxZg31H1VMyEUsjn0lMSmorK5efZAPnKn9C4jdvd\nVhmdnaBTXHv7xyUdG3nS2sJoJGhr0pa+KTbiwIDAQABAoIBAGz0vK6KrnpQlsSS\naPWwAVllJg+C9Yh7eAcYCyjutiPiTh1g+lVs50fOVfgTHKfXjfe7GqGp6IA0oT\nKC4ScvLaUWwxlqoO7liuh62XziZPaQQRH9oTgRBc7lvwJbgo4eNezEHj1eDLCTu\nxG3SvKUqXku4eiv540ni5PeiDomBjPrZy49Fh2XiARh3blC7zyn7IufCv76PsH\nsDDw3ZpNzTSdbhGnKt/aZQiHQiaLNjvqfD1/BBsVJj3UD1rpkWPW96mWyvdZMe\n1Lblzd+Y5cDEVkqah8RRzQNby1S2gBFrQBR6b3/T7Li2mJkiKJ03ikGm8lhYeg\npBlZRzoDlyOSo2ECgYEA6zIxlLwrPfQ1nyrIJyCbVBA3X4B2dv2DLND3NdaIVM\ntxOTSLjcvqf6K7qTRVWzSw0uiRnxN0ITiMmYIppwISVLo6eFWPo3i15lKZ2sY\n2a7wL2/R+u01UjwJXBIOtR4cEt1sOv4f9DpgdwB4pI/Srteo4FptgEndXPN2mq\ndVGDcCgYEA/qPwmbVgqJKUUjCqw8MeL8Tz83PCZDgpFzNv5d2M6d98ECiDMNS0u\naUrhvRUvR51C2ya5gjh/hAtgolpsH/AtRHFBaU1e2EpYNAPkMliImDW0OLEan\nK7/Io4SExswLQcSfjOeEp7hdOAcxcyUiKWFYuJyWYu3W77zorHtlIhU0CgYB6\nJiJMH3UwfhaeA2QLL+sdoxXYao/7bQa+o0MMrHjSM8zDA0v/okk/Ir1yIjRLU\nAeCVd5XltmGRiv3VXVh2VMP9ahEOXmMXAXmX+S7yD6qQoYd1ILFj00K66QQli\nXnrBrTYaa7yWjL7FAzWKqUNYGNOeEEWVPkRyGLg31381gQKBgE9AXMiqD7xHao\nwuA2fMGWAKr1ZM5pjJD7JToE/M/UyDh3FThdrjBffVS26a4k0qn70vTzs9NEq\n3c8rz04UZLi2IBjCs2OD+Ondt4p7cuR6OUFn4nOy49kUd7Hgv1Q2ejt3iWMc4\n1biXa70QEAZ7ZYlCKw69kkKm6N++h6ux4hdAoGAJ8oU8mZTS5xih3V4PCfyt9Z\nK+YC83VWm25v0WyjBSYuECmes1aEL95eOOre4fjdhr31BfpHhUiI6/8gHVsC\nNhA2mLpWBrNDjbdQgd9isY+hgpNBWinL0c7ZPqEkxg9hWkGWTekaHWTpKO7XS\nTbftlt8kgw4HvCPwyaOM9fl4b0=\n-----END RSA PRIVATE KEY-----"

# Save to file with UTF-8 encoding without BOM
import codecs
with codecs.open('kalshi_private.pem', 'w', encoding='utf-8') as f:
    f.write(key)

print("Saved working PEM file without BOM")

# Test with adapter
adapter = KalshiAdapter(
    kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
    kalshi_private_key=None  # Force loading from file
)

try:
    sig = adapter._generate_signature("123", "GET", "/test")
    print(f"✓ Signature generated: {sig[:50]}")
except Exception as e:
    print(f"✗ Error: {e}")
