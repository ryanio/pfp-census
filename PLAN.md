# Plan

## Status

Live at [ryanio.github.io/pfp-census](https://ryanio.github.io/pfp-census/) from the 2026-10-13 05:01 UTC snapshot: 3,176 profiles, 431 collections with wearers, 1,926 collections checked. The thread draft lives in `TWEETS.md`, which is gitignored and stays on the local machine.

## Before posting

1. Add the API key secret so the workflow can refresh. Run it yourself; the value never prints:
   ```sh
   ~/.claude/skills/onepassword/scripts/op-sa run --env-file ~/.config/op/opensea.env -- sh -c 'printf %s "$OPENSEA_API_KEY" | gh secret set OPENSEA_API_KEY -R ryanio/pfp-census'
   ```
   A dedicated key for this repo is easier to rotate than a shared one.
2. Run `gh workflow run pages.yml -R ryanio/pfp-census` about an hour before posting, then update the numbers in `TWEETS.md` from the fresh page.
3. Paste the link into the X composer and check that the card shows the map.
4. Check every handle in the thread. They come from each collection's OpenSea profile, and some look truncated.

## Refresh schedule

`.github/workflows/pages.yml` runs at 01:17 and 13:17 UTC. Scheduled runs refresh both times for the first 14 days after `LAUNCH_DATE`, only the 13:17 run until day 45, then Mondays only. Pushes and manual runs always refresh. Without the secret, every run deploys the committed snapshot in `site/`.

## Known limits

- Coverage is the seed list. A collection outside the top lists can have wearers and still be missing.
- The map shows 2,401 hexagons (a Gosper island of order 4), so with more than 2,401 profiles it samples in proportion.
- Face value uses floor price times wearers at snapshot USD prices from the payment token endpoint.

## Later

- A live "here now" counter was skipped to keep the page static. It needs a small backend (a Worker or any always-on server holding websockets).
- Snapshot history: keep a dated `counts.json` per refresh so the page can show which collections are gaining wearers.
- A sibling explorer for `GET /api/v2/nfts/group/{group}/facets` is planned in [ryanio/pop-report](https://github.com/ryanio/pop-report).
