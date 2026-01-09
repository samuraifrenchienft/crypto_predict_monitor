from limitless_sdk.api import HttpClient
from limitless_sdk.markets import MarketFetcher

c = HttpClient(base_url="https://api.limitless.exchange")
mf = MarketFetcher(c)

print("MARKET METHODS:")
print([x for x in dir(mf) if ("market" in x.lower()) and (not x.startswith("_"))])

print("\nPUBLIC METHODS:")
print([x for x in dir(mf) if not x.startswith("_")])
