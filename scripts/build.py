import hashlib, json, math, os, random, sys, time
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = sys.argv[1]
SEED, PROF, CACHE, SITE = (os.path.join(ROOT, p) for p in ("data/seed.json", "data/profiles", "data/img", "site"))
TILE, SH_COLS, SH_ROWS = int(os.environ.get("TILE", 80)), 20, 20
MINI, MI_COLS, MI_ROWS = 40, 50, 50
LOGO, LG_COLS = 64, 20
WALL_TOP, WALL_BUDGET = int(os.environ.get("WALL_TOP", 30)), int(os.environ.get("WALL_BUDGET", 3200))
RATE_MIN_OWNERS, RATE_MIN_WEARERS = 100, 5
os.makedirs(os.path.join(SITE, "s"), exist_ok=True)

seed = {c["slug"]: c for c in json.load(open(SEED))}
crawled = [json.load(open(os.path.join(PROF, f))) for f in sorted(os.listdir(PROF))]
fetched_at = max(d["fetched_at"] for d in crawled)
colls = sorted([d for d in crawled if d["count"] > 0], key=lambda d: -d["count"])

def img_path(url):
    if not url: return None
    p = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".png")
    return p if os.path.exists(p) else None

def pick(p): return p.get("profile_image_url") or p["nft_pfp"].get("image_url")

def tok_key(t):
    return (0, int(t), "") if t.isdigit() else (1, 0, t)

# USD prices for floor currencies, from the API's payment token endpoint
usd = {"USDC": 1.0, "USDG": 1.0, "USDT": 1.0}
if os.environ.get("OPENSEA_API_KEY"):
    from osapi import get
    native = {"ETH": ("ethereum", "0x0000000000000000000000000000000000000000"), "SOL": ("solana", "So11111111111111111111111111111111111111112"),
              "APE": ("ape_chain", "0x0000000000000000000000000000000000000000"), "RON": ("ronin", "0x0000000000000000000000000000000000000000"),
              "HYPE": ("hyperevm", "0x0000000000000000000000000000000000000000"), "MON": ("monad", "0x0000000000000000000000000000000000000000"),
              "POL": ("polygon", "0x0000000000000000000000000000000000000000")}
    for sym, (ch, addr) in native.items():
        s, b = get(f"/chain/{ch}/payment_token/{addr}")
        px = (b or {}).get("usdPrice") or (b or {}).get("usd_price")
        if s == 200 and px: usd[sym] = float(px)
        else: print("no usd price for", sym, s, file=sys.stderr)
    if "ETH" in usd: usd["WETH"] = usd["ETH"]
json.dump(usd, open(os.path.join(ROOT, "data/usd.json"), "w"))
print("usd", usd, file=sys.stderr)

C, P, all_imgs = [], [], []
for cid, d in enumerate(colls):
    sd = seed.get(d["slug"], {})
    contracts = []
    rows = []
    for p in d["profiles"]:
        n = p["nft_pfp"]; ck = (n["chain"], n["contract_address"].lower())
        if ck not in contracts: contracts.append(ck)
        u = p.get("username") or ""; dn = p.get("display_name") or ""
        rows.append({"r": [u, dn if dn and dn != u else "", p["address"], 1 if p.get("is_verified") else 0, n["token_id"], contracts.index(ck)], "img": pick(p)})
    rows.sort(key=lambda x: (x["r"][5], tok_key(x["r"][4])))
    sym = sd.get("floor_symbol") or ""
    floor = sd.get("floor") or None
    fu = floor * usd[sym] if floor and sym in usd else None
    C.append({"id": cid, "s": d["slug"], "n": sd.get("name") or d["slug"], "ch": (sd.get("contracts") or [{}])[0].get("chain") or (contracts[0][0] if contracts else ""),
              "o": sd.get("num_owners") or 0, "f": floor, "fs": sym, "fu": fu, "c": len(rows), "v": sum(x["r"][3] for x in rows),
              "tw": sd.get("twitter") or "", "cat": (sd.get("category") or "").lower(), "logo_url": sd.get("image_url"), "k": [list(x) for x in contracts]})
    P.append(rows)

total = sum(c["c"] for c in C)
print(f"collections with wearers: {len(C)}, profiles: {total}", file=sys.stderr)

def placeholder(size, label, hue_seed):
    rnd = random.Random(hue_seed)
    im = Image.new("RGB", (size, size), (rnd.randint(60, 120), rnd.randint(80, 130), rnd.randint(70, 120)))
    ImageDraw.Draw(im).text((size * .36, size * .3), (label or "?")[:1].upper(), fill=(235, 240, 236), font_size=int(size * .45))
    return im

def tile_img(url, size, label):
    p = img_path(url)
    if p:
        try: return Image.open(p).convert("RGB").resize((size, size), Image.LANCZOS)
        except Exception: pass
    return placeholder(size, label, url or label)

def write_sheets(tiles, size, cols, rows, pattern, quality):
    per = cols * rows; files = []
    for k in range(math.ceil(len(tiles) / per) or 1):
        sheet = Image.new("RGB", (cols * size, rows * size), (40, 48, 44))
        for j, (url, label) in enumerate(tiles[k * per:(k + 1) * per]):
            sheet.paste(tile_img(url, size, label), ((j % cols) * size, (j // cols) * size))
        fn = pattern.format(k); sheet.save(os.path.join(SITE, fn), "WEBP", quality=quality, method=6); files.append(fn)
    return files

# full sheets: every face, in collection then token order
go, tiles = 0, []
for c, rows in zip(C, P):
    c["go"] = go; go += len(rows)
    tiles += [(x["img"], x["r"][0] or x["r"][2][2:]) for x in rows]
sheet_files = write_sheets(tiles, TILE, SH_COLS, SH_ROWS, "s/{}.webp", 72)

# mini atlas: the faces the map shows. Big island: every collection is a territory. Phones: top 30 + the rest.
WALL_CELLS, SMALL_CELLS = 2401, 343  # Gosper islands of order 4 and 3
def allocate(counts, n):
    total = sum(counts); raw = [x * n / total for x in counts]
    a = [max(1, math.floor(x)) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: -(raw[i] - math.floor(raw[i])))
    k = 0
    while sum(a) < n: a[order[k % len(order)]] += 1; k += 1
    while sum(a) > n: a[a.index(max(a))] -= 1
    return a
def priority(rows, seed_):
    idx = list(range(len(rows))); random.Random(seed_).shuffle(idx)
    return sorted(idx, key=lambda i: (img_path(rows[i]["img"]) is None, -rows[i]["r"][3], rows[i]["r"][0] == ""))
alloc_full = allocate([c["c"] for c in C], WALL_CELLS) if len(C) <= WALL_CELLS else None
mini_tiles, mini_who, full, samples = [], [], [], []
for ci, (c, rows) in enumerate(zip(C, P)):
    want = max(min(5, len(rows)), alloc_full[ci] if alloc_full else 0)
    order = priority(rows, c["s"])[:want]
    c["ms"], c["mn"] = len(mini_tiles), min(5, len(order))
    tiles = list(range(len(mini_tiles), len(mini_tiles) + len(order)))
    mini_tiles += [(rows[i]["img"], rows[i]["r"][0] or rows[i]["r"][2][2:]) for i in order]
    mini_who += [c["go"] + i for i in order]
    samples.append(tiles)
    full.append({"id": c["id"], "label": c["n"], "count": c["c"], "tiles": tiles})
small = []
small_top = 30
rest_ids = list(range(small_top, len(C)))
counts_small = [c["c"] for c in C[:small_top]] + ([sum(C[i]["c"] for i in rest_ids)] if rest_ids else [])
alloc_small = allocate(counts_small, SMALL_CELLS)
for ci in range(min(small_top, len(C))):
    small.append({"id": C[ci]["id"], "label": C[ci]["n"], "count": C[ci]["c"], "tiles": samples[ci][:max(1, alloc_small[ci])]})
if rest_ids:
    pool = [t for i in rest_ids for t in samples[i]]
    random.Random("rest").shuffle(pool)
    small.append({"id": -1, "label": f"{len(rest_ids)} more collections", "count": counts_small[-1], "tiles": pool[:max(1, alloc_small[-1])]})
wall = {"full": full, "small": small}
per_tile = 1
mini_files = write_sheets(mini_tiles, MINI, MI_COLS, MI_ROWS, "m{}.webp", 70)

# logos
logo_tiles = []
for c in C:
    if c["logo_url"] and img_path(c["logo_url"]): c["lg"] = len(logo_tiles); logo_tiles.append((c["logo_url"], c["n"]))
    else: c["lg"] = -1
lg_rows = max(1, math.ceil(len(logo_tiles) / LG_COLS))
write_sheets(logo_tiles, LOGO, LG_COLS, lg_rows, "logos.webp", 80)

for c in C: c.pop("logo_url")
summary = {"at": fetched_at, "n": total, "k": len(crawled), "c": C,
           "sheet": {"cols": SH_COLS, "rows": SH_ROWS, "tile": TILE, "count": len(sheet_files)},
           "mini": {"cols": MI_COLS, "rows": MI_ROWS, "tile": MINI, "files": mini_files, "who": mini_who},
           "logos": {"cols": LG_COLS, "count": len(logo_tiles), "file": "logos.webp"},
           "wall": wall,
           "rateMinOwners": RATE_MIN_OWNERS, "rateMinWearers": RATE_MIN_WEARERS,
           "usdNote": ", ".join(f"1 {k} = ${v:,.2f}" for k, v in usd.items() if k in {c['fs'] for c in C} and k not in ("USDC", "USDG", "USDT", "WETH"))}
json.dump([[x["r"] for x in rows] for rows in P], open(os.path.join(SITE, "profiles.json"), "w"), separators=(",", ":"))
tpl = open(os.path.join(ROOT, "scripts/template.html")).read()
if os.environ.get("LOCAL"): tpl = tpl.replace("<meta charset=\"utf-8\">", "<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">", 1)
blob = json.dumps(summary, separators=(",", ":")).replace("</", "<\\/")
page = tpl.replace("/*__SUMMARY__*/", blob)
SITE_URL = os.environ.get("SITE_URL")
if SITE_URL:
    # standalone document for static hosting: real head, social card tags
    head_end = page.index("</style>") + len("</style>")
    head, body = page[:head_end], page[head_end:]
    head = head.replace('<meta charset="utf-8">\n', "")
    desc = f"{total:,} OpenSea profiles wear an NFT they hold as their picture, across {len(C)} collections. A map of who wears what."
    GA_ID = os.environ.get("GA_ID", "").strip()
    ga = (f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{GA_ID}");</script>
""" if GA_ID else "")
    meta = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="PFP Census">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:image" content="{SITE_URL}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="PFP Census">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{SITE_URL}og.png">
{ga}<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cpath d='M50 4 90 27v46L50 96 10 73V27z' fill='%230786FF'/%3E%3C/svg%3E">
"""
    page = "<!doctype html>\n<html lang=\"en\">\n<head>\n" + meta + head + "\n</head>\n<body>" + body + "\n</body>\n</html>\n"
open(os.path.join(SITE, "index.html"), "w").write(page)
sizes = {f: os.path.getsize(os.path.join(SITE, f)) for f in ["index.html", "profiles.json", "logos.webp"] + mini_files + sheet_files}
print(f"sheets={len(sheet_files)} mini={len(mini_files)} per_tile={per_tile} total_bytes={sum(sizes.values())/1e6:.1f}MB biggest={max(sizes.values())/1e6:.2f}MB", file=sys.stderr)
