import json, sys, concurrent.futures as cf
sys.path.insert(0, sys.argv[1])
from osapi import get
SEED = sys.argv[2]
CHAINS = ['blast', 'base', 'ethereum', 'zora', 'arbitrum', 'sei', 'avalanche', 'polygon', 'optimism', 'ape_chain', 'flow', 'soneium', 'ronin', 'bera_chain', 'solana', 'shape', 'unichain', 'gunzilla', 'abstract', 'animechain', 'hyperevm', 'somnia', 'monad', 'hyperliquid', 'megaeth', 'ink', 'robinhood', 'stablechain']
seed = json.load(open(SEED)); have = {c["slug"] for c in seed}
def lst(args):
    ch, ob = args
    s, b = get("/collections", {"chain": ch, "order_by": ob, "limit": 100})
    return ch, ob, (b or {}).get("collections", []) if s == 200 else []
new = {}
with cf.ThreadPoolExecutor(6) as ex:
    for ch, ob, cs in ex.map(lst, [(ch, ob) for ch in CHAINS for ob in ("seven_day_volume", "thirty_day_volume")]):
        for c in cs:
            if c["collection"] not in have and not c.get("is_nsfw") and not c.get("is_disabled") and c.get("contracts"):
                new.setdefault(c["collection"], c)
print("new collections:", len(new), file=sys.stderr)
def stats(c):
    s, b = get(f"/collections/{c['collection']}/stats")
    return c, ((b or {}).get("total", {}) if s == 200 else {})
with cf.ThreadPoolExecutor(6) as ex:
    for c, t in ex.map(stats, new.values()):
        seed.append({"slug": c["collection"], "name": c.get("name"), "image_url": c.get("image_url"), "category": c.get("category"),
                     "contracts": c.get("contracts"), "twitter": c.get("twitter_username"), "safelist": c.get("safelist_status"),
                     "num_owners": t.get("num_owners"), "floor": t.get("floor_price"), "floor_symbol": t.get("floor_price_symbol"),
                     "market_cap": t.get("market_cap"), "volume": t.get("volume")})
json.dump(seed, open(SEED, "w"), indent=1)
print("seed now", len(seed), file=sys.stderr)
