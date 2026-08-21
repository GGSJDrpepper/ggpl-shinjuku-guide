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
- `outputs/site/events.json`: tournament fallback data
- `outputs/site/tools/`: scripts for updating imported data
- `.github/workflows/update-pokerguild-events.yml`: scheduled PokerGuild tournament update
- `docs/`: GitHub Pages publish copy

When updating the site, copy `outputs/site` into `docs` before pushing to GitHub.

## Tournament Updates

GitHub Actions updates tournament data automatically every 30 minutes by running `outputs/site/tools/update-pokerguild-events.py`.

The workflow imports upcoming tournaments from PokerGuild, writes `outputs/site/events.json`, copies it to `docs/events.json`, and commits only when the data changed. GitHub Pages then republishes the site from `docs`.

You can also run it manually from GitHub: `Actions` → `Update PokerGuild events` → `Run workflow`.

If the automatic commit fails, check `Settings` → `Actions` → `General` → `Workflow permissions` and set it to `Read and write permissions`.
