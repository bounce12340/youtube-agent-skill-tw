#!/usr/bin/env python3
# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""把你已經收集好的清單，換成「相對該帳號自己中位數」的倍數。

    python3 swipe.py collected.json
    python3 swipe.py collected.json --min 2.0 --json

輸入是你自己整理的 JSON，一支片一個物件：

    [{"channel":"示範頻道","title":"...","views":12000,"url":"","duration":38}]

原始觀看數比較的是帳號大小，不是點子。40 萬在大型帳號可能是平常，
在中位數 3 萬的帳號就是值得看的異常。所以每支片都除以該帳號自己的中位數。
一個帳號少於四支，中位數沒有意義，工具會跳過並寫出來，而不是安靜地排噪音。

公式來自 skills/yt-script/hooks.json，比對的是標題字面。
它不是「這支片為什麼有觀看」的解釋，也不能預測下一支。

這個程式只讀本機檔案。它不上網、不登入、不讀取任何憑證。
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(HERE, "..", "yt-script", "hooks.json")
with open(HOOKS, encoding="utf-8") as _fh:
    FORMULAS = json.load(_fh)["hooks"]

UNCLASSIFIED = "未對上公式"


def classify(title: str) -> str:
    best = None
    hits = 0
    for formula in FORMULAS:
        matched = sum(1 for pattern in formula["match"] if re.search(pattern, title, re.IGNORECASE))
        if matched > hits:
            best, hits = formula, matched
    return best["name"] if best else UNCLASSIFIED


def rank(rows: list[dict], minimum: float = 1.5) -> dict:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("channel") or "未命名"), []).append(row)
    outliers = []
    thin = []
    for channel, videos in grouped.items():
        views = [float(video.get("views") or 0) for video in videos]
        if len(videos) < 4:
            thin.append({"channel": channel, "count": len(videos)})
            continue
        median = statistics.median(views) if views else 0
        for video in videos:
            count = float(video.get("views") or 0)
            multiple = (count / median) if median else 0
            outliers.append({
                "channel": channel,
                "title": video.get("title") or "",
                "views": int(count),
                "median": int(median),
                "multiple": round(multiple, 2),
                "formula": classify(video.get("title") or ""),
                "url": video.get("url") or "",
                "duration": video.get("duration"),
            })
    kept = [row for row in outliers if row["multiple"] >= minimum]
    kept.sort(key=lambda row: -row["multiple"])
    counts: dict[str, int] = {}
    for row in kept:
        counts[row["formula"]] = counts.get(row["formula"], 0) + 1
    return {
        "videos": len(rows),
        "channels": len(grouped),
        "minimum": minimum,
        "outliers": kept,
        "skipped_thin_channels": thin,
        "formula_counts": counts,
    }


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [item for item in args if item != "--json"]
    minimum = float(args[args.index("--min") + 1]) if "--min" in args else 1.5
    files = [item for item in args if not item.startswith("--") and not re.match(r"^[\d.]+$", item)]
    if not files or not os.path.exists(files[0]):
        print(__doc__)
        sys.exit(1)
    with open(files[0], encoding="utf-8") as fh:
        rows = json.load(fh)
    if isinstance(rows, dict):
        rows = rows.get("videos", [])
    report = rank(rows, minimum)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print(f"\n  {report['videos']} 支，{report['channels']} 個帳號，列出 {minimum} 倍以上\n")
    for row in report["outliers"][:25]:
        title = row["title"][:36]
        channel = row["channel"][:18]
        print(f"    {row['multiple']:5.2f}x  {row['views']:>9,}  對比中位數 {row['median']:>9,}  {channel:<18} {title}")
        print(f"            標題字面像：{row['formula']}")
    if not report["outliers"]:
        print("    沒有超過門檻。每個帳號再多收集幾支，或把 --min 調低。")
    thin = report["skipped_thin_channels"]
    if thin:
        shown = "、".join(f"{item['channel']}（{item['count']}）" for item in thin[:6])
        print(f"\n  略過 {len(thin)} 個不足 4 支的帳號。一兩支算不出中位數：{shown}")
    if report["formula_counts"]:
        print("\n  這些異常標題的字面公式（不是觀看原因）")
        for name, count in sorted(report["formula_counts"].items(), key=lambda item: -item[1]):
            print(f"    {count:2d}  {name}")
    print("\n  倍數只描述你這份清單裡、相對自己帳號的距離。不能預測下一支。\n")


if __name__ == "__main__":
    main()
