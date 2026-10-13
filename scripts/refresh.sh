#!/bin/sh
# Full refresh: seed collections, walk pfp-profiles for each, fetch avatars, build the site and social card.
# Needs OPENSEA_API_KEY in the environment. Output goes to site/.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
: "${OPENSEA_API_KEY:?set OPENSEA_API_KEY}"
: "${SITE_URL:=https://ryanio.github.io/pfp-census/}"
python3 scripts/seed.py "$ROOT/scripts" data/seed.json
python3 scripts/seed_chains.py "$ROOT/scripts" data/seed.json
rm -rf data/profiles
python3 scripts/crawl.py "$ROOT/scripts" data/seed.json data/profiles
# second pass retries any collection whose walk failed partway
python3 -c "
import json, os
d = 'data/profiles'
for f in os.listdir(d):
    if json.load(open(os.path.join(d, f)))['status'] != 'ok': os.remove(os.path.join(d, f))"
python3 scripts/crawl.py "$ROOT/scripts" data/seed.json data/profiles
mkdir -p data/img data/fonts
python3 scripts/images.py data/profiles data/seed.json data/img 96
for f in "ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf:bsd.ttf" "ofl/publicsans/PublicSans%5Bwght%5D.ttf:ps.ttf" "ofl/ibmplexmono/IBMPlexMono-Medium.ttf:mono.ttf"; do
  [ -f "data/fonts/${f##*:}" ] || curl -sfL -o "data/fonts/${f##*:}" "https://raw.githubusercontent.com/google/fonts/main/${f%%:*}"
done
rm -rf site
TILE=96 SITE_URL="$SITE_URL" python3 scripts/build.py "$ROOT"
python3 scripts/og.py "$ROOT"
python3 scripts/share.py "$ROOT"
