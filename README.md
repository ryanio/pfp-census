# PFP Census

A map of which NFT collections OpenSea users wear as their profile picture. Live at [ryanio.github.io/pfp-census](https://ryanio.github.io/pfp-census/).

Every count comes from walking [`GET /api/v2/collections/{slug}/pfp-profiles`](https://docs.opensea.io/reference/api-overview) to the end for each collection. A profile counts only when its NFT profile picture is verified, meaning the wallet holds that NFT right now. The endpoint has no total count, so the crawl pages through every collection in the seed list: the top collections on OpenSea by market cap and volume, overall and per chain, plus well-known PFP projects.

## How it works

`scripts/refresh.sh` seeds the collection list, crawls each collection, downloads the avatars, and builds `site/`: one HTML page, a `profiles.json`, and WebP sprite sheets. The page is static. The API key is only used by the crawl, never by the page.

The map lays collections along a [Gosper curve](https://en.wikipedia.org/wiki/Gosper_curve), the hexagonal space-filling curve, so each collection stays in one piece and its area tracks its wearers. Hexagons use the same rounded frame OpenSea draws around verified NFT profile pictures.

## Data

Each fresh crawl commits CSVs to `data/`: `collections.csv` (one row per collection: wearers, holders, wear rate, floor, face value) and `wearers.csv` (every counted profile with its collection, chain, contract and token). `data/history/` keeps an append-only record keyed by crawl time: `totals.csv` (headline numbers per crawl) and `collections.csv` (each collection per crawl), so you can chart who is gaining wearers.

## Refreshing

The `Refresh and deploy` workflow re-crawls twice a day for the first two weeks after launch, daily through day 30, then weekly on Mondays. With an `OPENSEA_API_KEY` repository secret it re-crawls and deploys fresh data. The built site is deployed straight to Pages and not committed. GitHub pauses scheduled workflows on repos with no activity for 60 days, so push anything or run it by hand to wake it.

To run it locally:

```sh
pip install "pillow>=11.2"   # plus rsvg-convert and ffmpeg for SVG and video avatars
OPENSEA_API_KEY=... ./scripts/refresh.sh
```
