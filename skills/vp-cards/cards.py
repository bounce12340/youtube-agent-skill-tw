#!/usr/bin/env python3
# Original checker. video-production-skills was inspected and not copied.
"""檢查疊字卡有沒有落在字幕的說話時間裡。不產生畫面，也不輸出 HTML。

    python3 cards.py cards.json --transcript captions.srt --json

同一錨點同時兩張卡會標出來。卡片文字寬度用該市場的手機寬度預設。
沒有對上任何一句字幕的卡，標成未對上時間，不是叫你刪掉。
"""
from __future__ import annotations

import json
import os
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
_EDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-edit")
for _path in (_LIB, _EDIT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from markets import MarketError, flag_terms, get_market, pop_market  # noqa: E402
from vpio import IoError, has_flag, load_json, pop_flag, public_issues, write_json  # noqa: E402
from zhtext import display_width  # noqa: E402


def _hit(card: dict, cues: list[tuple[float, float, str]]) -> bool:
    return any(card["start"] < end and start < card["end"] for start, end, _text in cues)


def check(data: dict, cues: list[tuple[float, float, str]], market: str = "tw") -> dict:
    profile = get_market(market)
    mobile = profile["layout"]["mobile_width"]
    cards = data.get("cards")
    issues: list[tuple[str, str]] = []
    if not isinstance(cards, list) or not cards:
        issues.append(("empty", "沒有疊字卡"))
        cards = []
    if not cues:
        issues.append(("no-transcript", "沒有字幕可對時間"))
    duration = data.get("duration")
    parsed = []
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            issues.append(("shape", f"第 {index + 1} 張不是物件"))
            continue
        label = str(card.get("id") or index + 1)
        anchor = str(card.get("anchor") or "bottom")
        text = str(card.get("text") or "")
        try:
            start = float(card.get("start"))
            end = float(card.get("end"))
        except (TypeError, ValueError):
            issues.append(("time", f"卡片 {label} 的起迄不是數字"))
            continue
        if end <= start:
            issues.append(("time", f"卡片 {label} 的結束沒有晚於開始"))
            continue
        if start < 0:
            issues.append(("time", f"卡片 {label} 從負的時間開始"))
        if isinstance(duration, (int, float)) and end > float(duration) + 0.05:
            issues.append(("overrun", f"卡片 {label} 超過宣告的總長"))
        if display_width(text) > mobile:
            issues.append((
                "wide-text",
                f"卡片 {label} 的顯示寬度 {display_width(text)}，超過可編輯預設 {mobile}",
            ))
        row = {"id": label, "start": start, "end": end, "text": text, "anchor": anchor}
        if cues and not _hit(row, cues):
            issues.append(("untimed", f"卡片 {label} 沒有和任何一句字幕重疊"))
        parsed.append(row)
    parsed.sort(key=lambda item: (item["anchor"], item["start"]))
    for index in range(1, len(parsed)):
        left, right = parsed[index - 1], parsed[index]
        if left["anchor"] == right["anchor"] and left["start"] < right["end"] and right["start"] < left["end"]:
            issues.append(("stack", f"錨點 {left['anchor']} 上 {left['id']} 和 {right['id']} 同時出現"))
    blob = "\n".join(item["text"] for item in parsed)
    return {
        "cards": len(parsed),
        "market": profile["id"],
        "locale": profile["locale"],
        "issues": issues,
        "term_flags": flag_terms(blob, profile["id"]),
    }


def main() -> None:
    try:
        market, args = pop_market(sys.argv[1:])
        out, args = pop_flag(args, "--out")
        transcript, args = pop_flag(args, "--transcript")
        overwrite = "--overwrite" in args
        args = has_flag(args, "--overwrite")
        as_json = "--json" in args
        args = has_flag(args, "--json")
        files = [item for item in args if not item.startswith("--")]
        if not files or not transcript:
            print(__doc__)
            sys.exit(1)
        if not os.path.exists(transcript):
            raise IoError("找不到字幕檔")
        from deadair import load

        report = check(load_json(files[0]), load(transcript), market)
    except MarketError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except (IoError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    report["issues"] = public_issues(report["issues"])
    if out:
        try:
            write_json(out, report, overwrite)
        except IoError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(3)
    if as_json or out:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print(f"\n  {report['cards']} 張卡  {report['locale']}\n")
    for item in report["issues"]:
        print(f"    x  {item['code']:<12} {item['message']}")
    if not report["issues"]:
        print("    卡片都落在字幕時間裡，同一錨點沒有疊在一起。")
    if report["term_flags"]:
        print(f"    用詞標示 {len(report['term_flags'])} 則，卡片文字沒有改。")
    print("  沒有產生畫面。\n")


if __name__ == "__main__":
    main()
