# GoodGame Poker Live Shinjuku International Visitor Guide

This repository contains a static multilingual visitor guide for GoodGame Poker Live Shinjuku.

The working site is in `outputs/site`.

The GitHub Pages publish copy is in `docs`, because GitHub Pages can publish from the repository root or `/docs` without a custom GitHub Actions workflow.

## Privacy note

The site includes `noindex,nofollow` and `robots.txt` so search engines are asked not to index it. Anyone who has the URL can still open the site.

## Main files

- `outputs/site/index.html`: page structure and content
- `outputs/site/styles.css`: visual design
- `outputs/site/app.js`: language switching, tournament display, amusement cash game price/rate display, Game ID guide
- `outputs/site/events.json`: fixed weekly tournament and amusement cash game data
- `outputs/site/tools/`: optional scripts for rebuilding imported data before manual review
- `.github/workflows/update-pokerguild-events.yml`: manual-only PokerGuild import helper
- `docs/`: GitHub Pages publish copy

When updating the site, copy `outputs/site` into `docs` before pushing to GitHub.

## Tournament Updates

The public guide now uses a fixed weekly tournament schedule. Visitors choose a weekday, and the site shows the tournaments assigned to that weekday.

The weekly schedule data was built from the current PokerGuild listings for GoodGame Poker Live Shinjuku. It is not refreshed automatically, because live PokerGuild and ring game reflections were unreliable for the reception/iPad use case.

To change the weekly schedule, edit `outputs/site/events.json`, copy it to `docs/events.json`, and push the change. The site also embeds the same fallback data in `app.js` so it works when `index.html` is opened directly from a computer.

The GitHub Action is manual-only now: `Actions` → `Manual PokerGuild event import` → `Run workflow`. Treat the result as a draft and review it before publishing.
