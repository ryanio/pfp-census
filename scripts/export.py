"""Write the census as CSV: the latest snapshot plus an append-only history keyed by crawl time."""
import csv, json, os, re, sys
ROOT = sys.argv[1]; SITE = os.path.join(ROOT, "site"); D = os.path.join(ROOT, "data"); H = os.path.join(D, "history"); os.makedirs(H, exist_ok=True)
S = json.loads(re.search(r'<script type="application/json" id="summary">(.*?)</script>', open(os.path.join(SITE, "index.html")).read(), re.S).group(1))
P = json.load(open(os.path.join(SITE, "profiles.json"))); C = S["c"]; AT = S["at"]
rate = lambda c: round(c["c"] / c["o"], 5) if c["o"] else ""
fv = lambda c: round(c["fu"] * c["c"], 2) if c["fu"] else ""
def write(name, header, rows):
    with open(os.path.join(D, name), "w", newline="") as f: w = csv.writer(f); w.writerow(header); w.writerows(rows)
def append(name, header, rows):
    path = os.path.join(H, name); fresh = not os.path.exists(path)
    if not fresh:
        with open(path) as f:
            if any(line.startswith(AT + ",") for line in f): return 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if fresh: w.writerow(header)
        w.writerows(rows)
    return len(rows)
by = sorted(C, key=lambda c: -c["c"])
cols = [[c["s"], c["n"], c["ch"], c["c"], c["o"], rate(c), c["v"], c["f"] if c["f"] is not None else "", c["fs"], round(c["fu"], 2) if c["fu"] else "", fv(c), c["tw"]] for c in by]
write("collections.csv", ["slug", "name", "chain", "wearers", "holders", "wear_rate", "verified_wearers", "floor", "floor_symbol", "floor_usd", "face_value_usd", "twitter"], cols)
wear = []
for c in by:
    for r in P[c["id"]]:
        k = c["k"][r[5]] if r[5] < len(c["k"]) else ["", ""]
        wear.append([c["s"], r[0], r[2], k[0], k[1], r[4], r[3]])
write("wearers.csv", ["collection", "username", "address", "chain", "contract", "token_id", "verified"], wear)
agg = {}
for c in C: agg[c["ch"]] = agg.get(c["ch"], 0) + c["c"]
total = [AT, S["n"], len(C), S["k"], len(agg), round(sum(fv(c) or 0 for c in C), 2), by[0]["s"], by[0]["c"], sum(1 for c in C if c["c"] == 1)]
a = append("totals.csv", ["at", "profiles", "collections_worn", "collections_checked", "chains", "face_value_usd", "top_collection", "top_wearers", "one_wearer_collections"], [total])
b = append("collections.csv", ["at", "slug", "wearers", "holders", "floor_usd"], [[AT, c["s"], c["c"], c["o"], round(c["fu"], 2) if c["fu"] else ""] for c in by])
print(f"export: {len(cols)} collections, {len(wear)} wearers; history +{a} totals, +{b} collections at {AT}")
