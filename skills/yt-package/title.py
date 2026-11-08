#!/usr/bin/env python3
# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""檢查短影音標題和封面文字是不是同一組。

    python3 title.py --title "前三秒先講完播" --cover "別自介"
    python3 title.py --title "..." --thumb "..."
    python3 title.py titles.txt
    python3 title.py --json --title "..."

標題和封面上的字是一組。封面把標題再寫一次，手機上就有一半畫面在重複。

寬度用東亞寬度：繁中、全形標點算 2，半形英文算 1，歧義字在台灣手機上算 2。
YouTube 標題硬上限仍是 100 個字元。桌面搜尋大約顯示寬度 60，手機大約 32。
這是近似，各平台截斷位置不一樣，也不能預測點擊。

封面文字顯示寬度超過 16（大約 8 個中文字）就會在直式封面上糊掉。
"""
from __future__ import annotations

import json
import os
import re
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from zhtext import (  # noqa: E402
    cjk_chars,
    display_width,
    has_figure,
    latin_words,
    truncate_display,
    vague_hits,
)

DESKTOP_W = 60
MOBILE_W = 32
COVER_W = 16
HARD_CHARS = 100

FRONT_BAD = (
    "今天我們",
    "大家好",
    "哈囉大家",
    "在開始之前",
    "分享一下",
    "這支影片想",
    "hey guys",
    "welcome back",
)

STOP_EN = {
    "the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are",
    "with", "your", "you", "my", "i", "this", "that", "it", "how", "what", "why",
}


def _tokens(text: str) -> set[str]:
    tokens = {word.lower() for word in latin_words(text) if word.lower() not in STOP_EN and len(word) > 2}
    chars = cjk_chars(text)
    for size in (2, 3, 4):
        for index in range(len(chars) - size + 1):
            tokens.add("".join(chars[index:index + size]))
    return tokens


def _cover_overlap(title: str, cover: str) -> list[str]:
    title_tokens = _tokens(title)
    cover_tokens = _tokens(cover)
    shared = title_tokens & cover_tokens
    # 只留沒有被更長詞包含的，避免「完播」「播率」「完播率」同時出現。
    kept = []
    for token in sorted(shared, key=len, reverse=True):
        if any(token != other and token in other for other in kept):
            continue
        kept.append(token)
    return kept[:8]


def check(title: str, cover: str | None = None) -> dict:
    text = title.strip()
    issues: list[tuple[str, str]] = []
    good: list[str] = []
    chars = len(text)
    width = display_width(text)
    if chars > HARD_CHARS:
        issues.append(("length", f"{chars} 個字元，超過平台標題硬上限 {HARD_CHARS}"))
    elif width > DESKTOP_W:
        issues.append(("length", f"顯示寬度 {width}，桌面搜尋大約在 {DESKTOP_W} 截斷"))
    else:
        good.append(f"顯示寬度 {width}，字元 {chars}，沒超過桌面近似上限")
    if width > MOBILE_W:
        head = truncate_display(text, MOBILE_W)
        issues.append(("mobile", f"手機大約只看得到「{head}」，確認主詞還在"))
    else:
        good.append(f"顯示寬度 {width}，手機寬度 {MOBILE_W} 以內")
    caps = [word for word in re.findall(r"[A-Za-z]+", text) if len(word) > 2 and word.isupper()]
    if len(caps) > 2:
        issues.append(("shouting", f"{len(caps)} 個全大寫英文單字，超過兩個就像垃圾訊息"))
    elif caps:
        good.append(f"{len(caps)} 個全大寫英文單字，還在強調範圍內")
    vague = vague_hits(text)
    if vague:
        issues.append(("vague", f"{'、'.join(vague)}：換成數字、名字或日期"))
    if has_figure(text):
        good.append("有具體數字或數量")
    else:
        issues.append(("no-number", "沒有數字、數量或日期，這是最常值得改的一點"))
    if text.endswith(("?", "？")):
        good.append("標題是一個開放問題")
    lowered = text.lower()
    if any(lowered.startswith(prefix) for prefix in FRONT_BAD):
        issues.append(("front-load", "開頭是寒暄或「分享一下」，主詞沒有放前面"))
    else:
        first_words = [word.lower() for word in latin_words(text)[:3]]
        if first_words and all(word in STOP_EN for word in first_words) and not cjk_chars(text[:8]):
            issues.append(("front-load", "前三個英文單字都是虛詞，主詞往前移"))
    if cover:
        cover_text = cover.strip()
        shared = _cover_overlap(text, cover_text)
        if shared:
            issues.append(("duplicate", f"封面和標題重複了 {'、'.join(shared)}。封面要講標題沒講的"))
        else:
            good.append("封面和標題用的是不同的詞")
        cover_w = display_width(cover_text)
        cover_words = latin_words(cover_text)
        if cover_w > COVER_W or len(cover_words) > 4:
            issues.append((
                "cover-length",
                f"封面顯示寬度 {cover_w}、英文 {len(cover_words)} 個單字。"
                f"直式封面大約 {COVER_W}（8 個中文字）或 4 個英文單字以內",
            ))
        else:
            good.append(f"封面顯示寬度 {cover_w}，手機上還讀得完")
    score = max(0, min(100, 100 - 14 * len(issues) + 4 * len(good)))
    return {
        "title": text,
        "chars": chars,
        "display_width": width,
        "score": score,
        "issues": issues,
        "good": good,
    }


def show(row: dict) -> None:
    print(f"\n  「{row['title']}」")
    print(f"  {row['chars']} 字元，顯示寬度 {row['display_width']}，分數 {row['score']}/100")
    for key, message in row["issues"]:
        print(f"    x  {key:<12} {message}")
    for message in row["good"]:
        print(f"    ok {'':<12} {message}")
    print("  分數是檢查清單，不是點擊預測。")


def _flag(args: list[str], name: str) -> str | None:
    if name not in args:
        return None
    return args[args.index(name) + 1]


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [item for item in args if item != "--json"]
    cover = _flag(args, "--cover")
    if cover is None:
        cover = _flag(args, "--thumb")
    if "--title" in args:
        rows = [check(args[args.index("--title") + 1], cover)]
    elif args and os.path.exists(args[0]) and not args[0].startswith("--"):
        with open(args[0], encoding="utf-8") as fh:
            rows = [check(line, cover) for line in fh.read().splitlines() if line.strip()]
    else:
        print(__doc__)
        sys.exit(1)
    rows.sort(key=lambda row: -row["score"])
    if as_json:
        public = []
        for row in rows:
            item = dict(row)
            item["issues"] = [{"code": key, "message": message} for key, message in row["issues"]]
            public.append(item)
        print(json.dumps(public, ensure_ascii=False, indent=1))
        return
    for row in rows:
        show(row)
    print()


if __name__ == "__main__":
    main()
