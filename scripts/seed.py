import json, sys, concurrent.futures as cf
sys.path.insert(0, sys.argv[1])
from osapi import get
OUT = sys.argv[2]

CURATED = """cryptopunks boredapeyachtclub mutant-ape-yacht-club azuki pudgypenguins lilpudgys milady doodles-official
proof-moonbirds clonex world-of-women-nft mfers cool-cats-nft nouns lil-nouns remilio-babies sproto-gremlins
kanpai-pandas bored-ape-kennel-club meebits elementals beanzofficial mocaverse captainz chimpers-nft cryptoadz-by-gremplin
hv-mtl otherdeed-expanded 0n1-force cyberkongz deadfellaz goblintownwtf kaiju-kingz onchainmonkey sappy-seals quirkies
rektguy y00ts degods degods-eth okay-bears mad-lads froganas claynosaurz retardio-cousins smilesss checks-vv-edition
the-plague the-memes-by-6529 wrapped-cryptopunks cryptopunks-v1-wrapped autoglyphs fidenza-by-tyler-hobbs chromie-squiggle-by-snowfro
pudgy-rods mutant-hounds normilio redacted-remilio-babies yayo-nft bitcoin-puppets nodemonkes ordinal-maxi-biz-omb
based-punks onchain-gaias basepaint toadz-on-base basedfellas the-warplets froggy-friends-official kemonokaki
guttercatgang parallel-alpha forgotten-runes-wizards-cult loot-for-adventurers lazy-lions sup-ducks 0xmons-xyz
gemesis opensea-gemesis gigaverse-roms finalbosu finalbosux bearish dyli moonbirds-mythics proof-collective
mutantcats rarible-cryptopunks persona-lamps tiny-dinos-eth anatoly mekaverse azuki-elementals pixelmongen1
cryptodickbutts-s3 lilpudgys wassies-by-wassies thewassies pudgy-present onchainkevin""".split()

def collection_list(order_by, pages):
    out, nxt = [], None
    for _ in range(pages):
        params = {"order_by": order_by, "limit": 100}
        if nxt: params["next"] = nxt
        s, b = get("/collections", params)
        if s != 200: print("list", order_by, s, file=sys.stderr); break
        out += b.get("collections", [])
        nxt = b.get("next")
        if not nxt: break
    return out

by_slug = {}
for ob, pages in [("market_cap", 3), ("thirty_day_volume", 2), ("seven_day_volume", 1)]:
    for c in collection_list(ob, pages):
        by_slug.setdefault(c["collection"], c)
print("from lists:", len(by_slug), file=sys.stderr)

missing = [s for s in dict.fromkeys(CURATED) if s not in by_slug]
def fetch_coll(slug):
    s, b = get(f"/collections/{slug}")
    return slug, s, b
with cf.ThreadPoolExecutor(6) as ex:
    for slug, s, b in ex.map(fetch_coll, missing):
        if s == 200 and b: by_slug.setdefault(b["collection"], b)
        else: print("skip curated", slug, s, file=sys.stderr)

colls = [c for c in by_slug.values() if not c.get("is_nsfw") and not c.get("is_disabled") and c.get("contracts")]
print("eligible:", len(colls), file=sys.stderr)

def stats(c):
    s, b = get(f"/collections/{c['collection']}/stats")
    t = (b or {}).get("total", {}) if s == 200 else {}
    return c["collection"], t
st = {}
with cf.ThreadPoolExecutor(6) as ex:
    for slug, t in ex.map(stats, colls):
        st[slug] = t

seed = []
for c in colls:
    t = st.get(c["collection"], {})
    seed.append({
        "slug": c["collection"], "name": c.get("name"), "image_url": c.get("image_url"),
        "category": c.get("category"), "contracts": c.get("contracts"),
        "twitter": c.get("twitter_username"), "safelist": c.get("safelist_status"),
        "num_owners": t.get("num_owners"), "floor": t.get("floor_price"), "floor_symbol": t.get("floor_price_symbol"),
        "market_cap": t.get("market_cap"), "volume": t.get("volume"),
    })
json.dump(seed, open(OUT, "w"), indent=1)
print("wrote", len(seed), file=sys.stderr)
