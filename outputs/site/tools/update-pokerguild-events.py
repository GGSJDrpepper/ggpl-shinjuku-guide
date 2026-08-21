#!/usr/bin/env python3
"""Import today's GoodGame Poker Live Shinjuku tournaments from PokerGuild.

The public site stays fast because it only reads events.json. This script is
meant to run on a schedule, during deployment, or manually before publishing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOM_URL = "https://pokerguild.jp/room?ik=4&tb=1"
TOURNAMENT_URL = "https://pokerguild.jp/tournament?ik={id}"
JST = dt.timezone(dt.timedelta(hours=9))


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; GoodGamePokerLiveShinjukuGuide/1.0; "
                "+https://ggpokerlive.jp/shinjuku/)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def clean_text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    lines = [" ".join(line.split()) for line in value.replace("\xa0", " ").splitlines()]
    return "\n".join(line for line in lines if line).strip()


class ClassTextCollector(HTMLParser):
    """Collect visible text from elements with selected CSS classes."""

    def __init__(self, target_classes: set[str]):
        super().__init__(convert_charrefs=True)
        self.target_classes = target_classes
        self.results: list[tuple[str, str]] = []
        self._capture_class = ""
        self._capture_depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._capture_class:
            self._capture_depth += 1
            if tag.lower() == "br":
                self._buffer.append("\n")
            return

        classes = set()
        for key, value in attrs:
            if key == "class" and value:
                classes.update(value.split())

        matched = classes & self.target_classes
        if matched:
            self._capture_class = sorted(matched)[0]
            self._capture_depth = 1
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if not self._capture_class:
            return

        self._capture_depth -= 1
        if self._capture_depth <= 0:
            text = clean_text("".join(self._buffer))
            if text:
                self.results.append((self._capture_class, text))
            self._capture_class = ""
            self._capture_depth = 0
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_class:
            self._buffer.append(data)


def yen_to_jpy(value: str) -> str:
    match = re.search(r"([\d,]+)\s*円", value)
    return f"{match.group(1)} JPY" if match else value


def points_to_stack(value: str) -> str:
    match = re.search(r"([\d,]+)\s*点", value)
    return match.group(1) if match else ""


def svg_time(block: str) -> str:
    tokens = re.findall(r"svg_num_(?:bold|medium)_(\d|colon)_svg", block)
    if not tokens:
        return ""
    return "".join(":" if token == "colon" else token for token in tokens[:5])


def date_from_label(label: str, today: dt.date) -> dt.date | None:
    match = re.search(r"(\d{2})\.(\d{2})", label)
    if not match:
        return None
    month, day = map(int, match.groups())
    try:
        candidate = dt.date(today.year, month, day)
    except ValueError:
        return None
    if candidate < today - dt.timedelta(days=180):
        return dt.date(today.year + 1, month, day)
    return candidate


TITLE_TRANSLATIONS = [
    (
        "【Lv.3終了時までのご着席で500円引き】",
        {
            "en": " [500 JPY off if seated by the end of Lv.3]",
            "zh": "【在Lv.3结束前入座可优惠500日元】",
            "zhTW": "【在Lv.3結束前入座可享500日圓優惠】",
            "zhHK": "【於Lv.3結束前入座可享500日圓優惠】",
            "ko": " [Lv.3 종료 전 착석 시 500엔 할인]",
        },
    ),
    (
        "【Lv.3終了時までのご着席で1,000円引き】",
        {
            "en": " [1,000 JPY off if seated by the end of Lv.3]",
            "zh": "【在Lv.3结束前入座可优惠1,000日元】",
            "zhTW": "【在Lv.3結束前入座可享1,000日圓優惠】",
            "zhHK": "【於Lv.3結束前入座可享1,000日圓優惠】",
            "ko": " [Lv.3 종료 전 착석 시 1,000엔 할인]",
        },
    ),
    (
        "【Lv.2終了時までのご着席で1,000円引き】",
        {
            "en": " [1,000 JPY off if seated by the end of Lv.2]",
            "zh": "【在Lv.2结束前入座可优惠1,000日元】",
            "zhTW": "【在Lv.2結束前入座可享1,000日圓優惠】",
            "zhHK": "【於Lv.2結束前入座可享1,000日圓優惠】",
            "ko": " [Lv.2 종료 전 착석 시 1,000엔 할인]",
        },
    ),
    (
        "【上位2名SPADIE2枚】",
        {
            "en": "[Top 2: 2 SPADIE tickets] ",
            "zh": "【前2名：2张SPADIE门票】",
            "zhTW": "【前2名：2張SPADIE門票】",
            "zhHK": "【前2名：2張SPADIE門票】",
            "ko": "[상위 2명: SPADIE 티켓 2장] ",
        },
    ),
    (
        "【上位5名合計15チケット】",
        {
            "en": "[Top 5: 15 tickets total] ",
            "zh": "【前5名合计15张门票】",
            "zhTW": "【前5名合計15張門票】",
            "zhHK": "【前5名合共15張門票】",
            "ko": "[상위 5명: 총 15장 티켓] ",
        },
    ),
    (
        "【上位3名戦国2枚】",
        {
            "en": "[Top 3: 2 SENGOKU tickets] ",
            "zh": "【前3名：2张SENGOKU门票】",
            "zhTW": "【前3名：2張SENGOKU門票】",
            "zhHK": "【前3名：2張SENGOKU門票】",
            "ko": "[상위 3명: SENGOKU 티켓 2장] ",
        },
    ),
    (
        "JOPTメガサテライト",
        {
            "en": "JOPT Mega Satellite",
            "zh": "JOPT大型卫星赛",
            "zhTW": "JOPT大型衛星賽",
            "zhHK": "JOPT大型衛星賽",
            "ko": "JOPT 메가 새틀라이트",
        },
    ),
]

PRIZE_TRANSLATIONS = [
    (
        "SPADIE権利",
        {
            "en": "SPADIE ticket",
            "ja": "SPADIE権利",
            "zh": "SPADIE参赛资格",
            "zhTW": "SPADIE參賽資格",
            "zhHK": "SPADIE參賽資格",
            "ko": "SPADIE 참가권",
        },
    ),
    (
        "JOPT権利",
        {
            "en": "JOPT ticket",
            "ja": "JOPT権利",
            "zh": "JOPT参赛资格",
            "zhTW": "JOPT參賽資格",
            "zhHK": "JOPT參賽資格",
            "ko": "JOPT 참가권",
        },
    ),
    (
        "戦国権利",
        {
            "en": "SENGOKU ticket",
            "ja": "戦国権利",
            "zh": "SENGOKU参赛资格",
            "zhTW": "SENGOKU參賽資格",
            "zhHK": "SENGOKU參賽資格",
            "ko": "SENGOKU 참가권",
        },
    ),
]

DETAIL_LANGS = (
    "en",
    "ja",
    "zh",
    "zhTW",
    "zhHK",
    "ko",
    "th",
    "vi",
    "id",
    "tl",
    "es",
    "fr",
    "de",
    "it",
    "ptBR",
)

PRIZE_DETAIL_REPLACEMENTS = {
    "en": {
        "活動支援": "Web Coin support",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "zh": {
        "活動支援": "Web Coin 支持",
        "戦国ポーカー": "战国扑克",
        "秋の陣": "秋之阵",
    },
    "zhTW": {
        "活動支援": "Web Coin 支援",
        "戦国ポーカー": "戰國撲克",
        "秋の陣": "秋之陣",
    },
    "zhHK": {
        "活動支援": "Web Coin 支援",
        "戦国ポーカー": "戰國撲克",
        "秋の陣": "秋之陣",
    },
    "ko": {
        "活動支援": "Web Coin 지원",
        "戦国ポーカー": "센고쿠 포커",
        "秋の陣": "가을의 진",
    },
    "th": {
        "活動支援": "การสนับสนุน Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "vi": {
        "活動支援": "hỗ trợ Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "id": {
        "活動支援": "dukungan Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "tl": {
        "活動支援": "Web Coin support",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "es": {
        "活動支援": "apoyo Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "fr": {
        "活動支援": "soutien Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "de": {
        "活動支援": "Web-Coin-Unterstützung",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "it": {
        "活動支援": "supporto Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
    "ptBR": {
        "活動支援": "apoio em Web Coin",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
    },
}

TICKET_COUNTERS = {
    "zh": "张",
    "zhTW": "張",
    "zhHK": "張",
    "ko": "장",
    "th": " ใบ",
    "vi": " vé",
    "id": " tiket",
    "tl": " tickets",
    "es": " entradas",
    "fr": " tickets",
    "de": " Tickets",
    "it": " ticket",
    "ptBR": " tickets",
}


def translate_title(title: str, lang: str) -> str:
    translated = title
    for source, replacements in TITLE_TRANSLATIONS:
        translated = translated.replace(source, replacements.get(lang, source))
    return " ".join(translated.split())


def localized_title(title: str) -> dict[str, str]:
    return {
        "en": translate_title(title, "en"),
        "ja": title,
        "zh": translate_title(title, "zh"),
        "zhTW": translate_title(title, "zhTW"),
        "zhHK": translate_title(title, "zhHK"),
        "ko": translate_title(title, "ko"),
    }


def translate_prize(prize: str, lang: str) -> str:
    translated = prize
    for source, replacements in PRIZE_TRANSLATIONS:
        translated = translated.replace(source, replacements.get(lang, source))
    separator = {
        "en": " / ",
        "zh": "、",
        "zhTW": "、",
        "zhHK": "、",
        "ko": " / ",
    }.get(lang, "・")
    return translated.replace("・", separator)


def localized_prize(prize: str) -> dict[str, str]:
    return {
        "en": translate_prize(prize, "en"),
        "ja": prize,
        "zh": translate_prize(prize, "zh"),
        "zhTW": translate_prize(prize, "zhTW"),
        "zhHK": translate_prize(prize, "zhHK"),
        "ko": translate_prize(prize, "ko"),
    }


def translate_prize_detail_line(line: str, lang: str) -> str:
    value = " ".join(line.split())
    if lang == "ja":
        return value

    for source, replacement in PRIZE_DETAIL_REPLACEMENTS.get(lang, {}).items():
        value = value.replace(source, replacement)

    if lang == "en":
        value = re.sub(
            r"(.+?Ticket)\s*(\d+)枚",
            lambda match: f"{match.group(2)} {match.group(1)}s",
            value,
        )
        value = re.sub(
            r"(.+?ticket)\s*(\d+)枚",
            lambda match: f"{match.group(2)} {match.group(1)}s",
            value,
        )
        value = re.sub(r"(\d+)枚", r"\1 tickets", value)
        return value

    counter = TICKET_COUNTERS.get(lang, " tickets")
    return re.sub(r"(\d+)枚", rf"\1{counter}", value)


def localized_prize_detail_lines(lines: list[str]) -> dict[str, list[str]]:
    return {
        lang: [translate_prize_detail_line(line, lang) for line in lines if line.strip()]
        for lang in DETAIL_LANGS
    }


def parse_prize_details(detail_html: str) -> list[dict[str, Any]]:
    collector = ClassTextCollector({"ggsj-contract-rank", "ggsj-contract-content"})
    collector.feed(detail_html)

    details: list[dict[str, Any]] = []
    pending_rank = ""
    for class_name, text in collector.results:
        if class_name == "ggsj-contract-rank":
            pending_rank = text
            continue

        if class_name != "ggsj-contract-content" or not pending_rank:
            continue

        lines = [line for line in text.splitlines() if line.strip()]
        if lines:
            details.append(
                {
                    "rank": pending_rank,
                    "items": localized_prize_detail_lines(lines),
                }
            )
        pending_rank = ""

    return details


def localized_description(prize: dict[str, str], end_time: str = "") -> dict[str, str]:
    en_prize = f" Prize: {prize['en']}." if prize.get("en") else ""
    ja_prize = f"プライズ: {prize['ja']}。" if prize.get("ja") else ""
    zh_prize = f"奖励: {prize['zh']}。" if prize.get("zh") else ""
    zh_tw_prize = f"獎勵: {prize['zhTW']}。" if prize.get("zhTW") else ""
    zh_hk_prize = f"獎賞: {prize['zhHK']}。" if prize.get("zhHK") else ""
    ko_prize = f"프라이즈: {prize['ko']}." if prize.get("ko") else ""
    end_text = f" Expected end: {end_time}." if end_time else ""
    ja_end = f"終了予定: {end_time}。" if end_time else ""
    zh_end = f"预计结束: {end_time}。" if end_time else ""
    zh_tw_end = f"預計結束: {end_time}。" if end_time else ""
    zh_hk_end = f"預計結束: {end_time}。" if end_time else ""
    ko_end = f" 종료 예정: {end_time}." if end_time else ""
    return {
        "en": f"Imported from PokerGuild for GoodGame Poker Live Shinjuku.{en_prize}{end_text} Check PokerGuild for full terms.",
        "ja": f"PokerGuildに掲載されたGoodGame Poker Live SHINJUKUのトーナメント情報です。{ja_prize}{ja_end}詳細条件はPokerGuildで確認してください。",
        "zh": f"此信息来自 PokerGuild 的 GoodGame Poker Live Shinjuku 赛程。{zh_prize}{zh_end}完整条件请查看 PokerGuild。",
        "zhTW": f"此資訊來自 PokerGuild 的 GoodGame Poker Live Shinjuku 賽程。{zh_tw_prize}{zh_tw_end}完整條件請查看 PokerGuild。",
        "zhHK": f"此資訊來自 PokerGuild 的 GoodGame Poker Live Shinjuku 賽程。{zh_hk_prize}{zh_hk_end}完整條件請查看 PokerGuild。",
        "ko": f"PokerGuild의 GoodGame Poker Live Shinjuku 토너먼트 정보입니다. {ko_prize}{ko_end} 자세한 조건은 PokerGuild에서 확인하세요.",
    }


def row_map_from_detail(detail_html: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for th, td in re.findall(
        r"<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>",
        detail_html,
        flags=re.S,
    ):
        key = clean_text(th)
        value = clean_text(td)
        if key:
            rows[key] = value
    return rows


def parse_detail(detail_html: str) -> dict[str, str]:
    rows = row_map_from_detail(detail_html)
    title_match = re.search(r'<h1 class="panel_title">(.*?)</h1>', detail_html, flags=re.S)
    title = clean_text(title_match.group(1)) if title_match else ""
    entry = rows.get("エントリ", "")
    re_entry = rows.get("リエントリ", "")
    return {
        "title": title,
        "date": rows.get("開催日", "").replace(".", "-"),
        "start": rows.get("開始時間", ""),
        "late": rows.get("受付締切", ""),
        "end": rows.get("終了予定", ""),
        "entry": yen_to_jpy(entry),
        "reEntry": yen_to_jpy(re_entry),
        "game": rows.get("ゲーム", ""),
        "prize": rows.get("プライズ", ""),
        "stack": points_to_stack(entry) or points_to_stack(re_entry),
    }


def split_room_boards(room_html: str) -> list[str]:
    section_match = re.search(
        r'<section class="list tournament_list">(.*?)(?:<section class="tab_game"|</article>)',
        room_html,
        flags=re.S,
    )
    section = section_match.group(1) if section_match else room_html
    return re.split(r'<div class="list_item_board">', section)[1:]


def parse_room_list(room_html: str, today: dt.date, days: int) -> list[dict[str, str]]:
    current_date: dt.date | None = None
    end_date = today + dt.timedelta(days=days)
    events: list[dict[str, str]] = []

    for board in split_room_boards(room_html):
        date_match = re.search(
            r'<div class="list_label_date[^>]*>.*?<label class="label_text">(.*?)</label>',
            board,
            flags=re.S,
        )
        if date_match:
            current_date = date_from_label(clean_text(date_match.group(1)), today)

        if (
            current_date is None
            or current_date < today
            or current_date > end_date
            or 'class="list_item"' not in board
        ):
            continue

        item_key = re.search(r'<div class="list_item"[^>]*data-itemkey="(\d+)"', board)
        title = re.search(r'<div class="item_main_title">(.*?)</div>', board, flags=re.S)
        price = re.search(r'<div class="item_icon_price_text">(.*?)</div>', board, flags=re.S)
        labels = [clean_text(label) for label in re.findall(r'<div class="label">(.*?)</div>', board, flags=re.S)]

        before_main = board.split('<div class="item_main">', 1)[0]
        open_block = before_main.split('<div class="item_time_due"', 1)[0]
        due_block = before_main.split('<div class="item_time_due"', 1)[1] if '<div class="item_time_due"' in before_main else ""

        key = item_key.group(1) if item_key else ""
        raw_title = clean_text(title.group(1)) if title else "Tournament"
        prize = labels[1] if len(labels) > 1 else ""

        events.append(
            {
                "id": key or re.sub(r"\W+", "-", raw_title).strip("-").lower(),
                "category": "tournament",
                "date": current_date.isoformat(),
                "start": svg_time(open_block),
                "late": svg_time(due_block),
                "titleText": raw_title,
                "entry": f"{clean_text(price.group(1))} JPY" if price else "",
                "reEntry": "",
                "addon": "",
                "game": labels[0] if labels else "",
                "stack": "",
                "prize": prize,
                "link": TOURNAMENT_URL.format(id=key) if key else ROOM_URL,
            }
        )

    return events


def detail_html_for(event_id: str, detail_dir: Path | None, fetch_details: bool) -> str:
    if detail_dir:
        for name in (
            f"pokerguild-tournament-{event_id}.html",
            f"tournament-{event_id}.html",
            f"{event_id}.html",
        ):
            path = detail_dir / name
            if path.exists():
                return path.read_text(encoding="utf-8")

    if not fetch_details:
        return ""

    return fetch_text(TOURNAMENT_URL.format(id=event_id))


def enrich_with_details(
    events: list[dict[str, str]],
    detail_dir: Path | None,
    fetch_details: bool,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for event in events:
        detail_html = detail_html_for(event["id"], detail_dir, fetch_details)
        detail = parse_detail(detail_html) if detail_html else {}

        title = detail.get("title") or event["titleText"]
        prize = detail.get("prize") or event.get("prize", "")
        prize_by_lang = localized_prize(prize)
        end_time = detail.get("end", "")
        prize_details = parse_prize_details(detail_html) if detail_html else []

        enriched.append(
            {
                "id": f"pokerguild-{event['id']}",
                "source": "PokerGuild",
                "sourceId": event["id"],
                "category": "tournament",
                "date": detail.get("date") or event["date"],
                "start": detail.get("start") or event["start"],
                "late": detail.get("late") or event["late"],
                "title": localized_title(title),
                "description": localized_description(prize_by_lang, end_time),
                "entry": detail.get("entry") or event["entry"],
                "reEntry": detail.get("reEntry") or event["reEntry"],
                "addon": "",
                "game": detail.get("game") or event["game"],
                "stack": detail.get("stack") or event["stack"],
                "prize": prize_by_lang,
                "prizeDetails": prize_details,
                "end": end_time,
                "link": event["link"],
            }
        )

    return enriched


def load_preserved_events(path: Path, today: dt.date) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    preserved = []
    for event in existing:
        if event.get("category") != "tournament" and event.get("category") in {"ring"}:
            event["date"] = today.isoformat()
            preserved.append(event)
    return preserved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--room-url", default=ROOM_URL)
    parser.add_argument("--room-html", type=Path, help="Use a saved PokerGuild room HTML file instead of fetching.")
    parser.add_argument("--detail-html-dir", type=Path, help="Directory containing saved detail HTML files.")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "events.json")
    parser.add_argument("--today", help="Override today's date, YYYY-MM-DD, in Japan time.")
    parser.add_argument("--days", type=int, default=14, help="How many days after today to include.")
    parser.add_argument("--no-fetch-details", action="store_true", help="Do not fetch detail pages for each tournament.")
    parser.add_argument("--replace-all", action="store_true", help="Do not preserve existing non-tournament events.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    today = (
        dt.date.fromisoformat(args.today)
        if args.today
        else dt.datetime.now(JST).date()
    )

    room_html = (
        args.room_html.read_text(encoding="utf-8")
        if args.room_html
        else fetch_text(args.room_url)
    )

    tournaments = parse_room_list(room_html, today, args.days)
    tournaments = enrich_with_details(
        tournaments,
        args.detail_html_dir,
        fetch_details=not args.no_fetch_details,
    )

    preserved = [] if args.replace_all else load_preserved_events(args.out, today)
    events = sorted(tournaments + preserved, key=lambda event: (event.get("date", ""), event.get("start", "")))

    args.out.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(events)} events ({len(tournaments)} tournaments for {today}) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
