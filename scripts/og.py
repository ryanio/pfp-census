"""Render the 1200x630 social card: title + headline numbers, and the Gosper island of real faces."""
import json, math, os, re, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); FONTS = os.path.join(ROOT, "data/fonts")
html = open(os.path.join(SITE, "index.html")).read()
S = json.loads(re.search(r'<script type="application/json" id="summary">(.*?)</script>', html, re.S).group(1))
K = 2  # supersample
W, H = 1200 * K, 630 * K
BG, INK, INK2, BLUE, GREEN = (12, 17, 23), (228, 234, 241), (150, 165, 182), (7, 134, 255), (15, 190, 57)
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

def font(path, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, path), size * K)
    if var: f.set_variation_by_name(var)
    return f

# Gosper island, order 4, same allocation and tiles as the page
def gosper(order):
    s = "A"
    for _ in range(order): s = "".join({"A": "A-B--B+A++AA+B-", "B": "+A-BB--B-A++A+B"}.get(c, c) for c in s)
    D = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
    pts, q, r, k = [(0, 0)], 0, 0, 0
    for c in s:
        if c in "AB": q += D[k][0]; r += D[k][1]; pts.append((q, r))
        elif c == "+": k = (k + 1) % 6
        elif c == "-": k = (k + 5) % 6
    return pts[:-1]
def allocate(counts, n):
    total = sum(counts); raw = [x * n / total for x in counts]
    a = [max(1, math.floor(x)) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: -(raw[i] - math.floor(raw[i])))
    k = 0
    while sum(a) < n: a[order[k % len(order)]] += 1; k += 1
    while sum(a) > n: a[a.index(max(a))] -= 1
    return a
pts = gosper(4); N = len(pts)
T = S["wall"]["full"]; alloc = allocate([t["count"] for t in T], N)
owner, tile = [], []
for ti, t in enumerate(T):
    for j in range(alloc[ti]): owner.append(ti); tile.append(t["tiles"][j % len(t["tiles"])])
SQ3 = math.sqrt(3)
xs = [SQ3 * (q + r / 2) for q, r in pts]; ys = [1.5 * r for _, r in pts]
minx, maxx, miny, maxy = min(xs) - SQ3 / 2, max(xs) + SQ3 / 2, min(ys) - 1, max(ys) + 1
box_w, box_h = 600 * K, 590 * K
R = min(box_w / (maxx - minx), box_h / (maxy - miny))
ox = W - 24 * K - (maxx - minx) * R; oy = (H - (maxy - miny) * R) / 2
cx = [ox + (x - minx) * R for x in xs]; cy = [oy + (y - miny) * R for y in ys]

# OpenSea rounded-hex mask
pct = re.findall(r"([\d.]+)%\s+([\d.]+)%", html[html.index("--hex:"):html.index("--hex:") + 3000])[:52]
HEX = [(float(a) / 100, float(b) / 100) for a, b in pct]
s = max(4, round(2 * R * 0.93))
mask = Image.new("L", (s * 4, s * 4), 0)
ImageDraw.Draw(mask).polygon([(x * s * 4, y * s * 4) for x, y in HEX], fill=255)
mask = mask.resize((s, s), Image.LANCZOS)
m = S["mini"]; sheets = [Image.open(os.path.join(SITE, f)).convert("RGB") for f in m["files"]]
for i in range(N):
    idx = tile[i]; col = idx % m["cols"]; row = idx // m["cols"]; sh = sheets[row // m["rows"]]; rr = row % m["rows"]
    face = sh.crop((col * m["tile"], rr * m["tile"], (col + 1) * m["tile"], (rr + 1) * m["tile"])).resize((s, s), Image.LANCZOS)
    img.paste(face, (round(cx[i] - s / 2), round(cy[i] - s / 2)), mask)
# channels between territories
at = {p: i for i, p in enumerate(pts)}
EN = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
def corner(i, k):
    a = math.radians(60 * k - 30); return (cx[i] + R * math.cos(a), cy[i] + R * math.sin(a))
lw = max(2, round(R * 0.42))
for i, (q, r) in enumerate(pts):
    for e in range(6):
        j = at.get((q + EN[e][0], r + EN[e][1]))
        if j is not None and j > i and owner[j] != owner[i]:
            d.line([corner(i, e), corner(i, e + 1)], fill=BG, width=lw)

# left column: title, numbers, source
L = 64 * K
kick = font("mono.ttf", 17)
d.text((L, 58 * K), "PFP CENSUS", font=kick, fill=BLUE)
title = font("bsd.ttf", 118, b"Black")
d.text((L, 88 * K), "WHO WEARS", font=title, fill=INK)
d.text((L, 88 * K + 104 * K), "WHAT", font=title, fill=INK)
bar_y = 88 * K + 104 * K * 2 + 22 * K
d.rectangle([L, bar_y, L + 120 * K, bar_y + 6 * K], fill=BLUE)
d.rectangle([L + 120 * K, bar_y, L + 180 * K, bar_y + 6 * K], fill=GREEN)
num = font("bsd.ttf", 54, b"ExtraBold"); lab = font("ps.ttf", 17, b"Medium"); mono = font("mono.ttf", 15)
stats = [(f"{S['n']:,}", "profiles wearing an NFT they hold"), (f"{len(S['c'])}", f"collections, of {S['k']:,} checked")]
y = bar_y + 34 * K
for v, t in stats:
    d.text((L, y), v, font=num, fill=INK)
    vw = d.textlength(v, font=num)
    d.text((L + vw + 14 * K, y + 26 * K), t, font=lab, fill=INK2)
    y += 66 * K
d.text((L, H - 64 * K), "By Ryan Ghods  ·  data from the OpenSea API", font=mono, fill=INK2)
img.resize((1200, 630), Image.LANCZOS).save(os.path.join(SITE, "og.png"), optimize=True)
print("og.png", os.path.getsize(os.path.join(SITE, "og.png")), "bytes; hex size", s // K, "px")
