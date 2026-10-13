"""Share pages and SEO for the built site.

For each highlight (one per chapter) and the most worn collections, write a 1200x630 preview image and a
small page at s/<id>/ whose Open Graph tags carry that image, then send readers on to the matching anchor.
Also fills the highlights strip, the static dek, JSON-LD and sitemap.xml in site/.
"""
import html, json, math, os, re, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); FONTS = os.path.join(ROOT, "data", "fonts")
SITE_URL = os.environ.get("SITE_URL", "https://ryanio.github.io/pfp-census/")
page = open(os.path.join(SITE, "index.html")).read()
S = json.loads(re.search(r'<script type="application/json" id="summary">(.*?)</script>', page, re.S).group(1))
C = S["c"]; N = S["n"]
os.makedirs(os.path.join(SITE, "s"), exist_ok=True)

BLUE = {"cryptopunks", "boredapeyachtclub", "mutant-ape-yacht-club", "pudgypenguins", "lilpudgys", "azuki", "milady", "doodles-official", "proof-moonbirds", "moonbirds", "clonex", "bored-ape-kennel-club", "meebits", "azuki-elementals", "wrapped-cryptopunks"}
CORE = ["boredapeyachtclub", "cryptopunks", "pudgypenguins", "azuki", "milady", "doodles-official"]
CHAINS = {"ethereum": "Ethereum", "base": "Base", "solana": "Solana", "polygon": "Polygon", "abstract": "Abstract", "ape_chain": "ApeChain", "ronin": "Ronin", "robinhood": "Robinhood Chain", "hyperevm": "HyperEVM", "ink": "Ink", "monad": "Monad", "arbitrum": "Arbitrum", "megaeth": "MegaETH"}
chain_name = lambda c: CHAINS.get(c, c.replace("_", " ").title())
rate = lambda c: c["c"] / c["o"] if c["o"] else 0
rate_ok = lambda c: c["o"] >= S["rateMinOwners"] and c["c"] >= S["rateMinWearers"]
fv = lambda c: (c["fu"] or 0) * c["c"]
pct = lambda r: f"{r * 100:.1f}%" if r >= 0.01 else f"{r * 100:.2f}%"
WORDS = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
def one_in(share):
    n = round(1 / share) if share else 0
    return f"one in {WORDS[n]}" if 2 <= n <= 10 and abs(1 / n - share) / share < 0.15 else f"{round(share * 100)}% of"
def money(v): return f"${v / 1e6:.1f} million" if v >= 1e6 else f"${round(v / 1000) * 1000:,.0f}"

by_worn = sorted(C, key=lambda c: -c["c"]); top, second = by_worn[0], by_worn[1]
rates = sorted([c for c in C if rate_ok(c)], key=lambda c: -rate(c))
core = sorted([c for c in (next((x for x in C if x["s"] == s), None) for s in CORE) if c and rate_ok(c)], key=lambda c: -c["o"])
fv_total = sum(fv(c) for c in C)
grails = sorted([c for c in C if c["fu"] and c["c"] >= 3], key=lambda c: -fv(c))
agg = {}
for c in C: a = agg.setdefault(c["ch"], {"ch": c["ch"], "n": 0, "k": 0, "ids": []}); a["n"] += c["c"]; a["k"] += 1; a["ids"].append(c["id"])
chains = sorted(agg.values(), key=lambda a: -a["n"])
singles = [c for c in C if c["c"] == 1]
slug_of = lambda c: "c-" + re.sub(r"[^a-z0-9-]", "", c["s"].lower())

# faces: global profile indices for a set of collections
def faces_of(cols, limit):
    out = []
    for c in cols:
        out += [c["go"] + i for i in range(c["c"])]
        if len(out) >= limit: break
    return out[:limit]

H = []
H.append({"id": "most-worn", "anchor": "most-worn", "kicker": "Most worn", "big": f"{top['c']:,}",
          "title": f"{top['n']} is the most worn NFT on OpenSea", "sub": f"{top['c']:,} people wear one they hold, about {top['c'] / second['c']:.0f}x the runner-up" if top["c"] / second["c"] >= 1.85 else f"{top['c']:,} people wear one they hold",
          "text": f"The most worn NFT on OpenSea is {top['n']}, with {top['c']:,} people wearing one they hold.", "faces": faces_of([top], 60)})
if rates:
    r1 = rates[0]; bc = max((rate(c) for c in core), default=0)
    H.append({"id": "wear-rate", "anchor": "wear-rate", "kicker": "Wear rate", "big": pct(rate(r1)),
              "title": f"{pct(rate(r1))} of {r1['n']} holders wear it as their face", "sub": f"Blue chips are all under {math.ceil(bc * 100)}%" if core else "",
              "text": f"{pct(rate(r1))} of {r1['n']} holders wear it as their OpenSea profile picture." + (f" The blue chips are all under {math.ceil(bc * 100)}%." if core else ""), "faces": faces_of(rates[:3], 60)})
if grails:
    H.append({"id": "grails", "anchor": "grails", "kicker": "Face value", "big": f"${fv_total / 1e6:.1f}M",
              "title": f"{money(fv_total)} of floor is worn as profile pictures", "sub": f"Led by {grails[0]['n']}, {grails[0]['c']} wearers",
              "text": f"{money(fv_total)} of NFT floor is being worn as OpenSea profile pictures right now.", "faces": faces_of(grails[:4], 60)})
if len(chains) > 1:
    c2 = chains[1]; share2 = c2["n"] / N
    H.append({"id": "chains", "anchor": "chains", "kicker": "Chains", "big": f"{round(share2 * 100)}%",
              "title": f"{one_in(share2).capitalize()} PFPs on OpenSea {'is' if one_in(share2).startswith('one in') else 'are'} on {chain_name(c2['ch'])}", "sub": f"From only {c2['k']} collections",
              "text": f"{one_in(share2).capitalize()} OpenSea profile pictures {'is an NFT' if one_in(share2).startswith('one in') else 'are NFTs'} on {chain_name(c2['ch'])}.", "faces": faces_of([C[i] for i in c2["ids"]], 60)})
H.append({"id": "long-tail", "anchor": "long-tail", "kicker": "One of one", "big": f"{len(singles)}",
          "title": f"{len(singles)} collections, one person each", "sub": "Someone wearing what nobody else here wears",
          "text": f"{len(singles)} NFT collections have exactly one person wearing them as an OpenSea profile picture.", "faces": [c["go"] for c in singles][:60]})
ENT = [{"id": slug_of(c), "anchor": c["s"], "kicker": chain_name(c["ch"]), "title": f"{c['c']:,} {'person wears' if c['c'] == 1 else 'people wear'} {c['n']}",
        "sub": (f"{pct(rate(c))} of holders wear it as their OpenSea PFP" if rate_ok(c) else "As their OpenSea profile picture"),
        "text": f"{c['c']:,} {'person wears' if c['c'] == 1 else 'people wear'} {c['n']} as their OpenSea profile picture" + (f", {pct(rate(c))} of holders." if rate_ok(c) else "."), "faces": faces_of([c], 60)} for c in by_worn[:40]]

# ---- images ----
K = 2; W, Hh = 1200 * K, 630 * K
BG, INK, INK2, BLUEC, GREEN = (11, 12, 15), (240, 242, 245), (160, 168, 180), (7, 134, 255), (15, 190, 57)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size * K)
    if var: f.set_variation_by_name(var)
    return f
sheets = {}
def tile(g, size):
    sh = S["sheet"]; per = sh["cols"] * sh["rows"]; k, j = divmod(g, per)
    if k not in sheets: sheets[k] = Image.open(os.path.join(SITE, "s", f"{k}.webp")).convert("RGB")
    t = sh["tile"]; return sheets[k].crop(((j % sh["cols"]) * t, (j // sh["cols"]) * t, (j % sh["cols"] + 1) * t, (j // sh["cols"] + 1) * t)).resize((size, size), Image.LANCZOS)
pcts = re.findall(r"([\d.]+)%\s+([\d.]+)%", page[page.index("--hex:"):page.index("--hex:") + 3000])[:52]
HEX = [(float(a) / 100, float(b) / 100) for a, b in pcts]
def hex_mask(size):
    m = Image.new("L", (size * 4, size * 4), 0); ImageDraw.Draw(m).polygon([(x * size * 4, y * size * 4) for x, y in HEX], fill=255)
    return m.resize((size, size), Image.LANCZOS)
def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width or not cur: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])
def render(h, path):
    img = Image.new("RGB", (W, Hh), BG); d = ImageDraw.Draw(img)
    # honeycomb of real faces on the right
    faces = h["faces"]; n = len(faces)
    if n:
        x0, x1, y0, y1 = 640 * K, 1170 * K, 40 * K, 590 * K
        cols = max(2, round(math.sqrt(n * (x1 - x0) / (y1 - y0) * 0.866)))
        rows = math.ceil(n / cols)
        s = int(min((x1 - x0) / (cols + 0.5) / 0.866, (y1 - y0) / (rows * 0.75 + 0.25)))
        s = min(s, 150 * K); sx, sy = 0.866 * s, 0.75 * s
        gw, gh = cols * sx + sx / 2, (rows - 1) * sy + s
        ox, oy = x0 + ((x1 - x0) - gw) / 2, y0 + ((y1 - y0) - gh) / 2
        m = hex_mask(int(s * 0.94)); ring = hex_mask(int(s))
        for k, g in enumerate(faces):
            r, c = divmod(k, cols); x = ox + c * sx + (sx / 2 if r % 2 else 0); y = oy + r * sy
            rim = Image.new("RGB", (int(s), int(s)), BLUEC if (r + c) % 3 else GREEN); img.paste(rim, (int(x), int(y)), ring)
            img.paste(tile(g, int(s * 0.94)), (int(x + s * 0.03), int(y + s * 0.03)), m)
    L, width = 64 * K, 540 * K
    d.text((L, 56 * K), h["kicker"].upper(), font=font("mono.ttf", 18), fill=BLUEC)
    size = 76
    while size > 40:
        f = font("bsd.ttf", size, b"ExtraBold"); lines = wrap(d, h["title"], f, width)
        if len(lines) <= 4: break
        size -= 4
    y = 92 * K
    for ln in lines: d.text((L, y), ln, font=f, fill=INK); y += int(size * 0.98 * K)
    d.rectangle([L, y + 18 * K, L + 110 * K, y + 24 * K], fill=BLUEC); d.rectangle([L + 110 * K, y + 18 * K, L + 170 * K, y + 24 * K], fill=GREEN)
    if h.get("sub"):
        for k, ln in enumerate(wrap(d, h["sub"], font("ps.ttf", 22, b"Medium"), width)[:2]):
            d.text((L, y + 44 * K + k * 32 * K), ln, font=font("ps.ttf", 22, b"Medium"), fill=INK2)
    d.text((L, Hh - 58 * K), "PFP CENSUS  ·  ryanio.github.io/pfp-census", font=font("mono.ttf", 15), fill=INK2)
    img.resize((1200, 630), Image.LANCZOS).save(path, optimize=True)

esc = lambda t: html.escape(t, quote=True)
def share_page(h):
    url, img = f"{SITE_URL}s/{h['id']}/", f"{SITE_URL}s/{h['id']}.png"
    dest = f"{SITE_URL}#{h['anchor']}"
    t = esc(h["title"]); dsc = esc(h["text"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t} · PFP Census</title>
<meta name="description" content="{dsc}">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="article"><meta property="og:site_name" content="PFP Census">
<meta property="og:title" content="{t}"><meta property="og:description" content="{dsc}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{t}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{t}"><meta name="twitter:description" content="{dsc}"><meta name="twitter:image" content="{img}">
<meta http-equiv="refresh" content="0; url={dest}">
<script>location.replace({json.dumps(dest)})</script>
</head><body style="font-family:system-ui;background:#0B0C0F;color:#F0F2F5"><p><a style="color:#fff" href="{dest}">{t}</a></p></body></html>
"""
for h in H + ENT:
    render(h, os.path.join(SITE, "s", f"{h['id']}.png"))
    os.makedirs(os.path.join(SITE, "s", h["id"]), exist_ok=True)
    open(os.path.join(SITE, "s", h["id"], "index.html"), "w").write(share_page(h))

# ---- page: highlights, share map, static dek, JSON-LD, sitemap ----
light = [{k: h[k] for k in ("id", "anchor", "kicker", "big", "title", "text")} for h in H]
shares = {h["anchor"]: h["id"] for h in ENT}
page = page.replace("/*__HIGHLIGHTS__*/", json.dumps({"h": light, "c": shares}, separators=(",", ":")).replace("</", "<\\/"))
dek = f"I counted every OpenSea profile whose picture is an NFT its owner still holds: {N:,} people across {len(C):,} collections and {len(chains)} chains. " + ("Here is who wears what." if top["s"] in BLUE else "The top of the list isn't who you'd expect.")
page = page.replace('<p class="dek" id="dek"></p>', f'<p class="dek" id="dek">{esc(dek)}</p>')
ld = [{"@context": "https://schema.org", "@type": "Article", "headline": "Who wears what: the PFP Census", "description": dek, "image": [SITE_URL + "og.png"],
       "author": {"@type": "Person", "name": "Ryan Ghods", "url": "https://github.com/ryanio"}, "datePublished": "2026-10-13", "dateModified": S["at"][:10], "mainEntityOfPage": SITE_URL},
      {"@context": "https://schema.org", "@type": "Dataset", "name": "PFP Census", "description": f"OpenSea profiles wearing a verified NFT profile picture, counted by collection: {N:,} profiles, {len(C):,} collections.",
       "url": SITE_URL, "creator": {"@type": "Person", "name": "Ryan Ghods"}, "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
       "keywords": ["NFT", "profile pictures", "PFP", "OpenSea", "onchain"], "dateModified": S["at"][:10],
       "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": SITE_URL + "profiles.json"}]}]
page = page.replace("</head>", '<script type="application/ld+json">' + json.dumps(ld, separators=(",", ":")) + "</script>\n</head>", 1)
open(os.path.join(SITE, "index.html"), "w").write(page)
open(os.path.join(SITE, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE_URL}</loc><lastmod>{S["at"][:10]}</lastmod><changefreq>daily</changefreq></url></urlset>\n')
print(f"share pages: {len(H)} highlights + {len(ENT)} collections")
