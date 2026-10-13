"""Download avatar + logo images into a local cache keyed by URL hash. Reads crawl output, writes nothing else."""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, urllib.request, urllib.parse, concurrent.futures as cf
from PIL import Image
PROFILES, SEED, CACHE, SIZE = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
os.makedirs(CACHE, exist_ok=True)

def sized(url):
    u = urllib.parse.urlsplit(url)
    if u.netloc.endswith("seadn.io"):
        q = dict(urllib.parse.parse_qsl(u.query)); q.update({"w": str(SIZE * 2), "auto": "format"})
        return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(q), ""))
    if url.startswith("ipfs://"):
        return "https://ipfs.io/ipfs/" + url[7:]
    return url

def key(url): return hashlib.sha1(url.encode()).hexdigest()

def fetch(url):
    path = os.path.join(CACHE, key(url) + ".png")
    if os.path.exists(path) or os.path.exists(path + ".fail"): return url, os.path.exists(path)
    try:
        req = urllib.request.Request(sized(url), headers={"user-agent": "Mozilla/5.0 pfp-census", "accept": "image/webp,image/png,image/avif,image/*;q=0.8,*/*;q=0.5"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read(25_000_000); ctype = r.headers.get("content-type", "")
        if "svg" in ctype or data[:200].lstrip().startswith((b"<svg", b"<?xml")):
            # untrusted SVG: rasterize from stdin, no files, no network
            data = subprocess.run(["rsvg-convert", "-w", str(SIZE * 2), "-h", str(SIZE * 2), "--keep-aspect-ratio"], input=data, capture_output=True, timeout=20, check=True).stdout
        elif ctype.startswith("video/") and shutil.which("ffmpeg"):
            with tempfile.TemporaryDirectory() as td:
                src = os.path.join(td, "v"); open(src, "wb").write(data)
                data = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, timeout=30, check=True).stdout
        im = Image.open(io.BytesIO(data)); im.seek(0)
        im = im.convert("RGBA")
        w, h = im.size; s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((SIZE, SIZE), Image.LANCZOS)
        bg = Image.new("RGBA", im.size, (128, 128, 128, 255)); bg.alpha_composite(im)
        bg.convert("RGB").save(path)
        return url, True
    except Exception as e:
        open(path + ".fail", "w").write(str(e)[:200])
        return url, False

def pick(p):
    return p.get("profile_image_url") or p["nft_pfp"].get("image_url")

urls = []
for f in sorted(os.listdir(PROFILES)):
    d = json.load(open(os.path.join(PROFILES, f)))
    urls += [pick(p) for p in d["profiles"] if pick(p)]
urls += [c["image_url"] for c in json.load(open(SEED)) if c.get("image_url")]
urls = list(dict.fromkeys(urls))
print("images:", len(urls), flush=True)
ok = bad = 0
with cf.ThreadPoolExecutor(24) as ex:
    for i, (u, good) in enumerate(ex.map(fetch, urls)):
        ok += good; bad += not good
        if (i + 1) % 1000 == 0: print(f"{i+1}/{len(urls)} ok={ok} fail={bad}", flush=True)
print(f"done ok={ok} fail={bad}", flush=True)
