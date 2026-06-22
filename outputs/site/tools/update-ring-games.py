#!/usr/bin/env python3
"""Import amusement cash game table status from the store Google Sheet."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any


SHEET_ID = "1e1WeSgafxL98fiBQgBm1_z1Wk96kuF9To5pdTlk_eKI"
GID = "1353500578"
JST = dt.timezone(dt.timedelta(hours=9))
TARGET_BLINDS = ("1-3", "2-5", "5-10", "10-20")
TABLE_GROUPS = {
    "A": (5, 8),
    "B": (9, 12),
    "C": (13, 16),
    "D": (17, 20),
    "E": (21, 24),
    "F": (25, 28),
    "G": (29, 32),
    "H": (33, 36),
}


def today_sheet_name() -> str:
    now = dt.datetime.now(JST)
    return f"{now.month}/{now.day}"


def fetch_sheet(sheet_id: str, gid: str, sheet_name: str | None) -> str:
    query = f"sheet={urllib.parse.quote(sheet_name)}" if sheet_name else f"gid={gid}"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json&{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GoodGamePokerLiveShinjukuGuide/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_jsonp(text: str) -> dict[str, Any]:
    match = re.search(r"setResponse\((.*)\);", text, flags=re.S)
    if not match:
        raise ValueError("Google Sheets response did not contain JSONP data")
    return json.loads(match.group(1))


def cell_value(cells: list[Any], index: int) -> str:
    if index >= len(cells) or not cells[index]:
        return ""
    value = cells[index].get("f") or cells[index].get("v") or ""
    return str(value).strip()


def format_time(raw: str) -> str:
    try:
        value = float(raw)
    except ValueError:
        return raw
    hour = int(value)
    minute = round((value - hour) * 60)
    return f"{hour:02d}:{minute:02d}"


def time_to_minutes(value: str) -> int:
    hour, minute = value.split(":", 1)
    return int(hour) * 60 + int(minute)


def grouped_games(active: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "blind": blind,
            "tableCount": sum(1 for active_blind in active.values() if active_blind == blind),
        }
        for blind in TARGET_BLINDS
    ]


def parse_timeline(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data["table"]["rows"]
    active: dict[str, str] = {}
    timeline = []

    for row in rows[3:]:
        cells = row.get("c", [])
        raw_time = cell_value(cells, 4)
        if not raw_time:
            continue
        formatted_time = format_time(raw_time)
        if not re.match(r"^\d{1,2}:\d{2}$", formatted_time):
            continue

        for table, (start, end) in TABLE_GROUPS.items():
            name, _, players, game = [cell_value(cells, index) for index in range(start, end + 1)]
            if game in TARGET_BLINDS:
                active[table] = game
            elif game:
                active.pop(table, None)
            if name == "〆" or players == "〆" or game == "〆" or players == "0":
                active.pop(table, None)

        games = grouped_games(active)
        timeline.append({"time": formatted_time, "games": games})

    return timeline


def current_snapshot(timeline: list[dict[str, Any]], as_of: str) -> dict[str, Any] | None:
    if not timeline:
        return None
    as_of_minutes = time_to_minutes(as_of)
    candidates = [entry for entry in timeline if time_to_minutes(entry["time"]) <= as_of_minutes]
    return candidates[-1] if candidates else timeline[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet-id", default=SHEET_ID)
    parser.add_argument("--gid", default=GID)
    parser.add_argument("--sheet-name", default=today_sheet_name())
    parser.add_argument("--input", type=Path, help="Use a saved Google Sheets JSONP response.")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "ring-games.json")
    parser.add_argument("--date-label")
    parser.add_argument("--as-of", default=dt.datetime.now(JST).strftime("%H:%M"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = args.input.read_text(encoding="utf-8") if args.input else fetch_sheet(args.sheet_id, args.gid, args.sheet_name)
    data = parse_jsonp(raw)
    timeline = parse_timeline(data)
    date_label = args.date_label or args.sheet_name or args.gid
    output = {
        "source": "Google Sheets",
        "sheetId": args.sheet_id,
        "gid": args.gid,
        "sheetName": args.sheet_name,
        "dateLabel": date_label,
        "asOf": args.as_of,
        "targetBlinds": list(TARGET_BLINDS),
        "current": current_snapshot(timeline, args.as_of),
        "timeline": timeline,
        "generatedAt": dt.datetime.now(JST).isoformat(timespec="seconds"),
    }
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} with {len(timeline)} ring-game time slots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
