# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""五個市場的本機設定。預設是台灣。

讀 skills/_lib/markets/*.json。不上網，也不把句子改寫成另一個市場的寫法。
澳門（mo）是獨立檔案，不是香港的別名。
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent / "markets"
IDS = ("tw", "hk", "mo", "sg", "cn")
DEFAULT = "tw"

REQUIRED = (
    "id", "locale", "name", "script", "default", "fillers", "vague", "quotes",
    "layout", "platforms", "platform_note", "example_hook", "example_title",
    "example_cover", "rules_note", "colloquial", "front_bad",
)


class MarketError(ValueError):
    pass


@lru_cache(maxsize=1)
def _load_all() -> dict[str, dict]:
    found = {}
    for code in IDS:
        path = HERE / f"{code}.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        if profile.get("id") != code:
            raise MarketError(f"{path.name} 的 id 應該是 {code}")
        if profile.get("alias_of"):
            raise MarketError(f"{code} 不能是另一個市場的別名")
        missing = [key for key in REQUIRED if key not in profile]
        if missing:
            raise MarketError(f"{code} 缺少 {', '.join(missing)}")
        found[code] = profile
    defaults = [code for code, profile in found.items() if profile.get("default")]
    if defaults != [DEFAULT]:
        raise MarketError("預設市場必須只有 tw")
    return found


@lru_cache(maxsize=1)
def terms() -> dict:
    return json.loads((HERE / "terms.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def sources() -> dict:
    return json.loads((HERE / "sources.json").read_text(encoding="utf-8"))


def get_market(code: str | None = None) -> dict:
    key = DEFAULT if code in (None, "") else str(code).lower()
    profiles = _load_all()
    if key not in profiles:
        joined = "、".join(IDS)
        raise MarketError(f"不認識的市場 {code}。可用 {joined}。")
    return profiles[key]


def pop_market(args: list[str]) -> tuple[str, list[str]]:
    """取出 --market，預設 tw。不改其餘參數的順序。"""
    market = DEFAULT
    kept: list[str] = []
    index = 0
    while index < len(args):
        item = args[index]
        if item == "--market":
            if index + 1 >= len(args):
                raise MarketError("`--market` 後面要接 tw、hk、mo、sg 或 cn。")
            market = args[index + 1]
            index += 2
            continue
        if item.startswith("--market="):
            market = item.split("=", 1)[1]
            index += 1
            continue
        kept.append(item)
        index += 1
    get_market(market)
    return market.lower(), kept


def _spans(text: str, phrase: str) -> list[tuple[int, int]]:
    spans = []
    if phrase.isascii():
        pattern = re.compile(rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])", re.IGNORECASE)
        spans.extend(match.span() for match in pattern.finditer(text))
        return spans
    start = 0
    while True:
        found = text.find(phrase, start)
        if found < 0:
            break
        spans.append((found, found + len(phrase)))
        start = found + len(phrase)
    return spans


def flag_terms(text: str, market: str = DEFAULT) -> list[dict]:
    """標出跨市場用詞、口語詞和字形。不回傳改寫後的句子。"""
    profile = get_market(market)
    profiles = _load_all()
    raw = terms()
    occupied = [False] * len(text)
    flags: list[dict] = []

    indexed = []
    for group in raw["groups"]:
        for code, phrases in group["by_market"].items():
            for phrase in phrases:
                indexed.append((phrase, group, code))
    indexed.sort(key=lambda item: len(item[0]), reverse=True)
    seen_span: set[tuple[int, int, str]] = set()
    for phrase, group, _code in indexed:
        for start, end in _spans(text, phrase):
            if any(occupied[start:end]):
                continue
            key = (start, end, group["id"])
            if key in seen_span:
                continue
            owners = [code for code, phrases in group["by_market"].items() if phrase in phrases]
            if market in owners:
                continue
            seen_span.add(key)
            for pos in range(start, end):
                occupied[pos] = True
            flags.append({
                "kind": "wording",
                "id": group["id"],
                "term": text[start:end],
                "action": "flag_only",
                "note": group["note"] + "工具沒有改寫原句。",
                "forms": group["by_market"],
                "seen_in": owners,
            })

    colloquial_owners: dict[str, list[str]] = {}
    for code, item in profiles.items():
        for phrase in item.get("colloquial") or []:
            colloquial_owners.setdefault(phrase, [])
            if code not in colloquial_owners[phrase]:
                colloquial_owners[phrase].append(code)
    for phrase in sorted(colloquial_owners, key=len, reverse=True):
        owners = colloquial_owners[phrase]
        if market in owners:
            continue
        for start, end in _spans(text, phrase):
            if any(occupied[start:end]):
                continue
            for pos in range(start, end):
                occupied[pos] = True
            flags.append({
                "kind": "colloquial",
                "id": "colloquial",
                "term": text[start:end],
                "action": "flag_only",
                "note": "這個詞在其他市場的粵語口語表。目前市場的預設沒有把它當成一般用詞。工具沒有改寫原句。",
                "forms": {code: [phrase] for code in owners},
                "seen_in": owners,
            })

    script = profile["script"]
    odd = []
    for index, char in enumerate(text):
        if occupied[index]:
            continue
        for traditional, simplified in raw["script_pairs"]:
            if script == "hant" and char == simplified:
                odd.append(char)
                break
            if script == "hans" and char == traditional:
                odd.append(char)
                break
    if odd:
        flags.append({
            "kind": "script",
            "id": "script",
            "term": "".join(dict.fromkeys(odd)),
            "action": "flag_only",
            "note": "這些字形和這份設定的預設字體不同。這是標示，不是轉換結果。用詞若不只差在字形，不要逐字替換。",
            "forms": {},
            "seen_in": [],
        })

    primary = profile["quotes"]["primary"]
    quote_hits = []
    if primary != "corner" and any(char in text for char in "「」『』"):
        quote_hits.append("「」")
    if primary != "curly" and any(char in text for char in "“”"):
        quote_hits.append("“”")
    if quote_hits:
        flags.append({
            "kind": "quote",
            "id": "quote",
            "term": "、".join(quote_hits),
            "action": "flag_only",
            "note": profile["quotes"]["note"] + "工具沒有改引號。",
            "forms": {"primary": [primary]},
            "seen_in": [],
        })
    return flags
