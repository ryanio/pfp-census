import json, os, sys, time, concurrent.futures as cf
sys.path.insert(0, sys.argv[1])
from osapi import get
SEED, OUTDIR = sys.argv[2], sys.argv[3]
MAX_PAGES = 400
os.makedirs(OUTDIR, exist_ok=True)
seed = json.load(open(SEED))

def crawl(c):
    slug = c["slug"]
    path = os.path.join(OUTDIR, slug + ".json")
    if os.path.exists(path):
        return slug, json.load(open(path))["count"], "cached"
    profiles, cursor, pages, status = [], None, 0, "ok"
    while True:
        params = {"limit": 100}
        if cursor: params["cursor"] = cursor
        s, b = get(f"/collections/{slug}/pfp-profiles", params)
        if s != 200:
            status = f"http {s}: {json.dumps(b)[:160] if b else ''}"
            break
        profiles += b.get("profiles", [])
        cursor, pages = b.get("next"), pages + 1
        if not cursor: break
        if pages >= MAX_PAGES: status = "capped"; break
    if status.startswith("http") and not profiles:
        return slug, -1, status
    json.dump({"slug": slug, "count": len(profiles), "pages": pages, "status": status, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "profiles": profiles}, open(path, "w"))
    return slug, len(profiles), status

t0 = time.time()
done = 0
with cf.ThreadPoolExecutor(6) as ex:
    for slug, n, status in ex.map(crawl, seed):
        done += 1
        if n != 0 or status != "ok":
            print(f"[{done}/{len(seed)}] {slug}: {n} ({status})", flush=True)
print(f"done in {time.time()-t0:.0f}s", flush=True)
