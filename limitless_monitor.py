import os
import json
import traceback
import requests
from dotenv import load_dotenv

load_dotenv()
WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

BASE = "https://api.limitless.exchange"

def discord_alert(msg: str) -> None:
    if not WEBHOOK:
        print("[WARN] DISCORD_WEBHOOK_URL missing in .env")
        return
    try:
        r = requests.post(WEBHOOK, json={"content": msg}, timeout=10)
        print("[OK] discord_status=", r.status_code)
    except Exception as e:
        print("[WARN] Discord post failed:", e)

def main():
    print("[INFO] cwd=", os.getcwd())

    # Try common markets endpoints; first one that returns 200 wins.
    candidates = [
        f"{BASE}/markets",
        f"{BASE}/api/markets",
        f"{BASE}/v1/markets",
    ]

    last_err = None
    for url in candidates:
        try:
            r = requests.get(url, timeout=20)
            print("[INFO] GET", url, "->", r.status_code)
            if r.status_code == 200:
                payload = r.json()
                with open("limitless_markets.json", "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                print("[OK] wrote limitless_markets.json")
                discord_alert("Limitless monitor online")
                return
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Could not fetch markets from any candidate endpoint. last_err={last_err}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("[ERROR] exception:")
        traceback.print_exc()
        raise
