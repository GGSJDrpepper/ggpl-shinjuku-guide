#!/usr/bin/env python3
"""Import upcoming GoodGame Poker Live Shinjuku tournaments from PokerGuild.

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


TITLE_TRANSLATIONS = [
    (
        "【Lv.3終了時までのご着席で500円引き】",
        {
            "en": " [500 JPY off if seated by the end of Lv.3]",
            "zh": "【在Lv.3结束前入座可优惠500日元】",
            "zhTW": "【在Lv.3結束前入座可享500日圓優惠】",
            "zhHK": "【於Lv.3結束前入座可享500日圓優惠】",
            "ko": " [Lv.3 종료 전 착석 시 500엔 할인]",
            "th": " [ลด 500 เยน หากนั่งก่อนจบ Lv.3]",
            "vi": " [giảm 500 yên nếu ngồi trước khi Lv.3 kết thúc]",
            "id": " [diskon 500 yen jika duduk sebelum Lv.3 berakhir]",
            "tl": " [500 yen discount if seated before Lv.3 ends]",
            "es": " [500 yenes de descuento si te sientas antes de terminar Lv.3]",
            "fr": " [500 yens de réduction si assis avant la fin du Lv.3]",
            "de": " [500 Yen Rabatt bei Sitzplatz bis Ende Lv.3]",
            "it": " [sconto di 500 yen se ti siedi entro la fine del Lv.3]",
            "ptBR": " [desconto de 500 ienes se sentado antes do fim do Lv.3]",
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
            "th": " [ลด 1,000 เยน หากนั่งก่อนจบ Lv.3]",
            "vi": " [giảm 1.000 yên nếu ngồi trước khi Lv.3 kết thúc]",
            "id": " [diskon 1.000 yen jika duduk sebelum Lv.3 berakhir]",
            "tl": " [1,000 yen discount if seated before Lv.3 ends]",
            "es": " [1.000 yenes de descuento si te sientas antes de terminar Lv.3]",
            "fr": " [1 000 yens de réduction si assis avant la fin du Lv.3]",
            "de": " [1.000 Yen Rabatt bei Sitzplatz bis Ende Lv.3]",
            "it": " [sconto di 1.000 yen se ti siedi entro la fine del Lv.3]",
            "ptBR": " [desconto de 1.000 ienes se sentado antes do fim do Lv.3]",
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
            "th": " [ลด 1,000 เยน หากนั่งก่อนจบ Lv.2]",
            "vi": " [giảm 1.000 yên nếu ngồi trước khi Lv.2 kết thúc]",
            "id": " [diskon 1.000 yen jika duduk sebelum Lv.2 berakhir]",
            "tl": " [1,000 yen discount if seated before Lv.2 ends]",
            "es": " [1.000 yenes de descuento si te sientas antes de terminar Lv.2]",
            "fr": " [1 000 yens de réduction si assis avant la fin du Lv.2]",
            "de": " [1.000 Yen Rabatt bei Sitzplatz bis Ende Lv.2]",
            "it": " [sconto di 1.000 yen se ti siedi entro la fine del Lv.2]",
            "ptBR": " [desconto de 1.000 ienes se sentado antes do fim do Lv.2]",
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
            "th": "[อันดับ 1-2: ตั๋ว SPADIE 2 ใบ] ",
            "vi": "[Top 2: 2 vé SPADIE] ",
            "id": "[Top 2: 2 tiket SPADIE] ",
            "tl": "[Top 2: 2 SPADIE tickets] ",
            "es": "[Top 2: 2 entradas SPADIE] ",
            "fr": "[Top 2 : 2 tickets SPADIE] ",
            "de": "[Top 2: 2 SPADIE-Tickets] ",
            "it": "[Top 2: 2 ticket SPADIE] ",
            "ptBR": "[Top 2: 2 tickets SPADIE] ",
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
            "th": "[Top 5: รวมตั๋ว 15 ใบ] ",
            "vi": "[Top 5: tổng cộng 15 vé] ",
            "id": "[Top 5: total 15 tiket] ",
            "tl": "[Top 5: 15 tickets total] ",
            "es": "[Top 5: 15 entradas en total] ",
            "fr": "[Top 5 : 15 tickets au total] ",
            "de": "[Top 5: insgesamt 15 Tickets] ",
            "it": "[Top 5: 15 ticket totali] ",
            "ptBR": "[Top 5: 15 tickets no total] ",
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
            "th": "[อันดับ 1-3: ตั๋ว SENGOKU 2 ใบ] ",
            "vi": "[Top 3: 2 vé SENGOKU] ",
            "id": "[Top 3: 2 tiket SENGOKU] ",
            "tl": "[Top 3: 2 SENGOKU tickets] ",
            "es": "[Top 3: 2 entradas SENGOKU] ",
            "fr": "[Top 3 : 2 tickets SENGOKU] ",
            "de": "[Top 3: 2 SENGOKU-Tickets] ",
            "it": "[Top 3: 2 ticket SENGOKU] ",
            "ptBR": "[Top 3: 2 tickets SENGOKU] ",
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
            "th": "JOPT Mega Satellite",
            "vi": "JOPT Mega Satellite",
            "id": "JOPT Mega Satellite",
            "tl": "JOPT Mega Satellite",
            "es": "JOPT Mega Satellite",
            "fr": "JOPT Mega Satellite",
            "de": "JOPT Mega Satellite",
            "it": "JOPT Mega Satellite",
            "ptBR": "JOPT Mega Satellite",
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
            "th": "SPADIE ticket",
            "vi": "vé SPADIE",
            "id": "tiket SPADIE",
            "tl": "SPADIE ticket",
            "es": "entrada SPADIE",
            "fr": "ticket SPADIE",
            "de": "SPADIE-Ticket",
            "it": "ticket SPADIE",
            "ptBR": "ticket SPADIE",
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
            "th": "JOPT ticket",
            "vi": "vé JOPT",
            "id": "tiket JOPT",
            "tl": "JOPT ticket",
            "es": "entrada JOPT",
            "fr": "ticket JOPT",
            "de": "JOPT-Ticket",
            "it": "ticket JOPT",
            "ptBR": "ticket JOPT",
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
            "th": "SENGOKU ticket",
            "vi": "vé SENGOKU",
            "id": "tiket SENGOKU",
            "tl": "SENGOKU ticket",
            "es": "entrada SENGOKU",
            "fr": "ticket SENGOKU",
            "de": "SENGOKU-Ticket",
            "it": "ticket SENGOKU",
            "ptBR": "ticket SENGOKU",
        },
    ),
]

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


TITLE_TERM_REPLACEMENTS = {
    "en": {
        "戦国ポーカーツアー": "SENGOKU Poker Tour",
        "戦国 ポーカーメガサテライト": "SENGOKU Poker Mega Satellite",
        "戦国ポーカーメガサテライト": "SENGOKU Poker Mega Satellite",
        "戦国ポーカー": "SENGOKU Poker",
        "秋の陣": "Autumn",
        "関ヶ原の戦い": "Battle of Sekigahara",
    },
    "zh": {
        "戦国ポーカーツアー": "战国扑克巡回赛",
        "戦国 ポーカーメガサテライト": "战国扑克大型卫星赛",
        "戦国ポーカーメガサテライト": "战国扑克大型卫星赛",
        "戦国ポーカー": "战国扑克",
        "秋の陣": "秋之阵",
        "関ヶ原の戦い": "关原之战",
    },
    "zhTW": {
        "戦国ポーカーツアー": "戰國撲克巡迴賽",
        "戦国 ポーカーメガサテライト": "戰國撲克大型衛星賽",
        "戦国ポーカーメガサテライト": "戰國撲克大型衛星賽",
        "戦国ポーカー": "戰國撲克",
        "秋の陣": "秋之陣",
        "関ヶ原の戦い": "關原之戰",
    },
    "zhHK": {
        "戦国ポーカーツアー": "戰國撲克巡迴賽",
        "戦国 ポーカーメガサテライト": "戰國撲克大型衛星賽",
        "戦国ポーカーメガサテライト": "戰國撲克大型衛星賽",
        "戦国ポーカー": "戰國撲克",
        "秋の陣": "秋之陣",
        "関ヶ原の戦い": "關原之戰",
    },
    "ko": {
        "戦国ポーカーツアー": "센고쿠 포커 투어",
        "戦国 ポーカーメガサテライト": "센고쿠 포커 메가 새틀라이트",
        "戦国ポーカーメガサテライト": "센고쿠 포커 메가 새틀라이트",
        "戦国ポーカー": "센고쿠 포커",
        "秋の陣": "가을의 진",
        "関ヶ原の戦い": "세키가하라 전투",
    },
}


def generic_title_phrase(match: re.Match[str], lang: str) -> str:
    capped = bool(match.group(1))
    place_count = match.group(2)
    ticket_name = match.group(3).upper()
    ticket_count = match.group(4)
    ticket_name = "SENGOKU" if "戦国" in match.group(3) else ticket_name

    if lang == "ja":
        return match.group(0)

    if lang == "en":
        prefix = "Up to top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} {ticket_name} tickets] "
    if lang == "zh":
        prefix = "最多前" if capped else "前"
        return f"【{prefix}{place_count}名：{ticket_count}张{ticket_name}门票】"
    if lang in {"zhTW", "zhHK"}:
        prefix = "最多前" if capped else "前"
        return f"【{prefix}{place_count}名：{ticket_count}張{ticket_name}門票】"
    if lang == "ko":
        prefix = "최대 상위" if capped else "상위"
        return f"[{prefix} {place_count}명: {ticket_name} 티켓 {ticket_count}장] "
    if lang == "th":
        prefix = "สูงสุด Top" if capped else "Top"
        return f"[{prefix} {place_count}: ตั๋ว {ticket_name} {ticket_count} ใบ] "
    if lang == "vi":
        prefix = "Tối đa top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} vé {ticket_name}] "
    if lang == "id":
        prefix = "Maks. top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} tiket {ticket_name}] "
    if lang == "es":
        prefix = "Hasta top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} entradas {ticket_name}] "
    if lang == "fr":
        prefix = "Jusqu'au top" if capped else "Top"
        return f"[{prefix} {place_count} : {ticket_count} tickets {ticket_name}] "
    if lang == "de":
        prefix = "Bis Top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} {ticket_name}-Tickets] "
    if lang == "it":
        prefix = "Fino alla top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} ticket {ticket_name}] "
    if lang == "ptBR":
        prefix = "Até top" if capped else "Top"
        return f"[{prefix} {place_count}: {ticket_count} tickets {ticket_name}] "
    return f"[Top {place_count}: {ticket_count} {ticket_name} tickets] "


def translate_title(title: str, lang: str) -> str:
    translated = title
    for source, replacements in TITLE_TRANSLATIONS:
        translated = translated.replace(source, replacements.get(lang, source))
    translated = re.sub(
        r"【(最大)?上位(\d+)名(SPADIE|戦国)(\d+)枚】",
        lambda match: generic_title_phrase(match, lang),
        translated,
    )
    for source, replacement in TITLE_TERM_REPLACEMENTS.get(lang, TITLE_TERM_REPLACEMENTS["en"]).items():
        translated = translated.replace(source, replacement)
    if lang == "en":
        translated = re.sub(r"(Tour)(\d{4})", r"\1 \2", translated)
    return " ".join(translated.split())


def localized_title(title: str) -> dict[str, str]:
    return {lang: translate_title(title, lang) for lang in DETAIL_LANGS}


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
    return {lang: translate_prize(prize, lang) for lang in DETAIL_LANGS}


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
    templates = {
        "en": (
            "Imported from PokerGuild for GoodGame Poker Live Shinjuku.",
            " Prize: {prize}.",
            " Expected end: {end}.",
            " Check PokerGuild for full terms.",
        ),
        "ja": (
            "PokerGuildに掲載されたGoodGame Poker Live SHINJUKUのトーナメント情報です。",
            "プライズ: {prize}。",
            "終了予定: {end}。",
            "詳細条件はPokerGuildで確認してください。",
        ),
        "zh": (
            "此信息来自 PokerGuild 的 GoodGame Poker Live Shinjuku 赛程。",
            "奖励: {prize}。",
            "预计结束: {end}。",
            "完整条件请查看 PokerGuild。",
        ),
        "zhTW": (
            "此資訊來自 PokerGuild 的 GoodGame Poker Live Shinjuku 賽程。",
            "獎勵: {prize}。",
            "預計結束: {end}。",
            "完整條件請查看 PokerGuild。",
        ),
        "zhHK": (
            "此資訊來自 PokerGuild 的 GoodGame Poker Live Shinjuku 賽程。",
            "獎賞: {prize}。",
            "預計結束: {end}。",
            "完整條件請查看 PokerGuild。",
        ),
        "ko": (
            "PokerGuild의 GoodGame Poker Live Shinjuku 토너먼트 정보입니다.",
            " 프라이즈: {prize}.",
            " 종료 예정: {end}.",
            " 자세한 조건은 PokerGuild에서 확인하세요.",
        ),
        "th": (
            "ข้อมูลนี้นำเข้าจาก PokerGuild สำหรับ GoodGame Poker Live Shinjuku.",
            " รางวัล: {prize}.",
            " เวลาจบโดยประมาณ: {end}.",
            " โปรดตรวจสอบเงื่อนไขทั้งหมดใน PokerGuild.",
        ),
        "vi": (
            "Thông tin được nhập từ PokerGuild cho GoodGame Poker Live Shinjuku.",
            " Giải thưởng: {prize}.",
            " Dự kiến kết thúc: {end}.",
            " Vui lòng kiểm tra điều kiện đầy đủ trên PokerGuild.",
        ),
        "id": (
            "Informasi ini diimpor dari PokerGuild untuk GoodGame Poker Live Shinjuku.",
            " Hadiah: {prize}.",
            " Perkiraan selesai: {end}.",
            " Periksa PokerGuild untuk syarat lengkap.",
        ),
        "tl": (
            "Imported from PokerGuild for GoodGame Poker Live Shinjuku.",
            " Prize: {prize}.",
            " Expected end: {end}.",
            " Check PokerGuild for full terms.",
        ),
        "es": (
            "Importado desde PokerGuild para GoodGame Poker Live Shinjuku.",
            " Premio: {prize}.",
            " Final estimado: {end}.",
            " Consulta PokerGuild para ver todos los términos.",
        ),
        "fr": (
            "Importé depuis PokerGuild pour GoodGame Poker Live Shinjuku.",
            " Prix : {prize}.",
            " Fin estimée : {end}.",
            " Consultez PokerGuild pour les conditions complètes.",
        ),
        "de": (
            "Von PokerGuild für GoodGame Poker Live Shinjuku importiert.",
            " Preis: {prize}.",
            " Voraussichtliches Ende: {end}.",
            " Vollständige Bedingungen auf PokerGuild prüfen.",
        ),
        "it": (
            "Importato da PokerGuild per GoodGame Poker Live Shinjuku.",
            " Premio: {prize}.",
            " Fine prevista: {end}.",
            " Controlla PokerGuild per i termini completi.",
        ),
        "ptBR": (
            "Importado do PokerGuild para GoodGame Poker Live Shinjuku.",
            " Prêmio: {prize}.",
            " Término previsto: {end}.",
            " Confira os termos completos no PokerGuild.",
        ),
    }

    descriptions: dict[str, str] = {}
    for lang in DETAIL_LANGS:
        intro, prize_text, end_text, footer = templates[lang]
        description = intro
        if prize.get(lang):
            description += prize_text.format(prize=prize[lang])
        if end_time:
            description += end_text.format(end=end_time)
        description += footer
        descriptions[lang] = description
    return descriptions


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
