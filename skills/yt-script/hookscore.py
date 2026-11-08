#!/usr/bin/env python3
# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""給短影音開頭一句打五項分數。這是啟發式，不能預測會不會被大量觀看。

    python3 hookscore.py --hook "為什麼你會在第三秒滑走？"
    python3 hookscore.py hooks.txt
    python3 hookscore.py --json hooks.txt

五項各 0 到 100。總評是平均的六成，加上最弱那項的四成。
最弱項權重是故意的：四項很強、一項是死的，人就從死的那項滑走。平均會把這個洞藏起來。

對象是 Shorts、Reels、TikTok 的前 1 到 3 秒，不是長片的前 15 秒。
中文約 4.5 字／秒，英文約 2.5 個單字／秒，只是口播粗估。

上游曾用 74 段英文短片自動字幕做過校準。那次校準分得開故意寫壞的開頭和真的開頭，
幾乎分不開同一位創作者自己的熱門和冷門。這份繁中改編沒有用台灣影片重做那次校準。
低分代表值得重寫。高分不是承諾。
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
    ADDRESS,
    CLOSED_EN,
    CLOSED_ZH,
    CURIOSITY_EN,
    CURIOSITY_ZH,
    STAKE_EN,
    STAKE_ZH,
    clamp,
    figure_spans,
    filler_hits,
    find_zh_phrases,
    spoken_seconds,
    vague_hits,
)

HERE = os.path.dirname(os.path.abspath(__file__))
UNCLASSIFIED = "未對上公式"

with open(os.path.join(HERE, "hooks.json"), encoding="utf-8") as _fh:
    FORMULAS = json.load(_fh)["hooks"]

FIX = {
    "SPECIFICITY": "把一個形容詞換成數字、名字或日期",
    "ADDRESS": "前 12 個字裡要出現「你」或 you",
    "STAKES": "講出照舊做法會失去什麼",
    "CURIOSITY": "把已經自問自答的那半句刪掉",
    "BREVITY": "口播大約 1 到 3 秒。中文約 5 到 14 個字，英文約 3 到 8 個單字",
}

LABEL = {
    "SPECIFICITY": "具體",
    "ADDRESS": "對準你",
    "STAKES": "代價",
    "CURIOSITY": "好奇",
    "BREVITY": "短",
    "VERDICT": "總評",
}


def specificity(text: str) -> int:
    figures = len(figure_spans(text))
    vague = len(vague_hits(text))
    filler = len(filler_hits(text))
    score = 34 + figures * 22 - vague * 16 - filler * 5
    named = sum(1 for word in text.split()[1:] if word[:1].isupper() and word[1:2].islower())
    score += min(18, 6 * named)
    if re.search(r"「[^」]{1,12}」", text):
        score += 12
    return clamp(score)


def address(text: str) -> int:
    hits = len(ADDRESS.findall(text))
    head = text[:12]
    first = 30 if ADDRESS.search(head) or ADDRESS.search(" ".join(text.split()[:6])) else 0
    return clamp(26 + hits * 20 + first)


def stakes(text: str) -> int:
    hits = len(find_zh_phrases(text, STAKE_ZH)) + len(STAKE_EN.findall(text))
    bonus = 14 if figure_spans(text) else 0
    return clamp(22 + hits * 26 + bonus)


def curiosity(text: str) -> int:
    hits = len(find_zh_phrases(text, CURIOSITY_ZH)) + len(CURIOSITY_EN.findall(text))
    question = 18 if text.strip().endswith(("?", "？")) else 0
    closed = -18 if find_zh_phrases(text, CLOSED_ZH) or CLOSED_EN.search(text) else 0
    return clamp(24 + hits * 17 + question + closed)


def brevity(text: str) -> int:
    seconds = spoken_seconds(text)
    if seconds <= 0:
        return 0
    if 1.0 <= seconds <= 3.0:
        return 100
    if seconds < 1.0:
        return clamp(100 - (1.0 - seconds) * 70, low=20)
    return clamp(100 - (seconds - 3.0) * 16, low=8)


PROPS = (
    ("SPECIFICITY", specificity),
    ("ADDRESS", address),
    ("STAKES", stakes),
    ("CURIOSITY", curiosity),
    ("BREVITY", brevity),
)


def classify(text: str) -> tuple[str, int]:
    best = None
    hits = 0
    for formula in FORMULAS:
        matched = sum(1 for pattern in formula["match"] if re.search(pattern, text, re.IGNORECASE))
        if matched > hits:
            best, hits = formula, matched
    if not best:
        return UNCLASSIFIED, 0
    return best["name"], hits


def band(verdict: int) -> str:
    if verdict >= 72:
        return "STRONG"
    if verdict >= 55:
        return "WORKABLE"
    return "WEAK"


BAND_ZH = {"STRONG": "強", "WORKABLE": "可用", "WEAK": "弱"}


def score(text: str) -> dict:
    parts = {name: fn(text) for name, fn in PROPS}
    values = list(parts.values())
    if not text.strip() or not values:
        verdict = 0
    else:
        verdict = round(0.6 * (sum(values) / len(values)) + 0.4 * min(values))
    name, hits = classify(text)
    weakest = min(parts, key=parts.get) if parts else "BREVITY"
    return {
        "hook": text.strip(),
        "properties": parts,
        "verdict": verdict,
        "band": band(verdict),
        "formula": name,
        "matched": hits,
        "weakest": weakest,
        "spoken_seconds": round(spoken_seconds(text), 2),
    }


def report(row: dict) -> None:
    text = row["hook"]
    print(f"\n  {text}")
    print(f"  {'-' * min(72, max(20, len(text)))}")
    for key, value in row["properties"].items():
        print(f"    {LABEL[key]:<6} {value:3d}  {'#' * (value // 5)}")
    print(f"    {LABEL['VERDICT']:<6} {row['verdict']:3d}  {BAND_ZH[row['band']]}")
    print(f"    口播約 {row['spoken_seconds']} 秒（粗估，前 1 到 3 秒才是短影音開頭）")
    if row["matched"]:
        print(f"    公式    {row['formula']}（對上 {row['matched']} 條字面規則）")
    else:
        print(f"    公式    {row['formula']}（多半是摘要，不是開頭）")
    print(f"    最弱    {LABEL[row['weakest']]}：{FIX[row['weakest']]}")
    print("    提醒    高分不能預測觀看或完播。")


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [item for item in args if item != "--json"]
    if "--hook" in args:
        lines = [args[args.index("--hook") + 1]]
    elif args and os.path.exists(args[0]):
        with open(args[0], encoding="utf-8") as fh:
            lines = [line for line in fh.read().splitlines() if line.strip()]
    else:
        print(__doc__)
        sys.exit(1)
    rows = [score(line) for line in lines]
    rows.sort(key=lambda row: -row["verdict"])
    if as_json:
        public = []
        for row in rows:
            item = {key: value for key, value in row.items() if key != "matched"}
            public.append(item)
        print(json.dumps(public, ensure_ascii=False, indent=1))
        return
    for row in rows:
        report(row)
    if len(rows) > 1:
        print(f"\n  較高的一句：{rows[0]['hook']}（{rows[0]['verdict']}，{BAND_ZH[rows[0]['band']]}）")
        print("  這只是五項啟發式的排序，不是熱門預測。\n")


if __name__ == "__main__":
    main()
