import base64

key = "MIIEogIBAAKCAQEA+laawbVft544HxmAoQ3ibmnmH1BH5uEYU7fvEGxDzT3x2kwa"
print(f"Key length: {len(key)}")
print(f"Is base64? {all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in key)}")

try:
    decoded = base64.b64decode(key)
    print(f"Decoded length: {len(decoded)}")
    print(f"First 50 bytes (hex): {decoded[:50].hex()}")
    asn1_header = b'\x30'
    print(f"Looks like ASN.1 DER: {decoded[:1] == asn1_header}")
except Exception as e:
    print(f"Base64 decode error: {e}")
