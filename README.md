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
- `outputs/site/events.json`: PokerGuild tournament data and fixed amusement cash game data
- `outputs/site/tools/`: optional scripts for rebuilding imported data before manual review
- `.github/workflows/update-pokerguild-events.yml`: scheduled and manual PokerGuild tournament updater
- `docs/`: GitHub Pages publish copy

When updating the site, copy `outputs/site` into `docs` before pushing to GitHub.

## Tournament Updates

The public guide reads the latest published `docs/events.json` file. GitHub Actions refreshes the tournament data from PokerGuild four times per day: 00:00, 06:00, 12:00, and 18:00 in Japan time.

The update script imports the upcoming GoodGame Poker Live Shinjuku tournaments from PokerGuild, including start time, late registration, entry, re-entry, starting stack, prize label, and ranked prize details when PokerGuild exposes them in the event detail page.

The amusement cash game section is fixed store-rule data. It is not updated from the live ring-game table sheet.

For urgent updates, run the workflow manually: `Actions` → `Update PokerGuild tournament data` → `Run workflow`. GitHub Pages usually reflects the new JSON within a few minutes.

Directly opening `index.html` from a computer does not run the automatic update. Use the GitHub Pages URL for the live version.
