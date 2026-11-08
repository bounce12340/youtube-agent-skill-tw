#!/usr/bin/env python3
# Original checker. video-production-skills was inspected and not copied.
# Upstream of the YouTube adaptation remains MIT. See LICENSE and upstream-video.json.
"""檢查本機分鏡表的時間是否接得上，畫面字是否放得下。

    python3 board.py storyboard.json
    python3 board.py storyboard.json --market mo --json

這不是開頭評分，也不預測觀看。口播秒數沿用全市場共用的粗估。
畫面字寬度用該市場的可編輯預設，不是平台規格。
"""
from __future__ import annotations

import json
import os
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from markets import MarketError, flag_terms, get_market, pop_market  # noqa: E402
from vpio import IoError, has_flag, load_json, pop_flag, public_issues, write_json  # noqa: E402
from zhtext import display_width, spoken_seconds  # noqa: E402

GAP_SECONDS = 0.35


def check(data: dict, market: str = "tw") -> dict:
    profile = get_market(market)
    mobile = profile["layout"]["mobile_width"]
    shots = data.get("shots")
    issues: list[tuple[str, str]] = []
    if not isinstance(shots, list) or not shots:
        issues.append(("empty", "分鏡表沒有鏡頭"))
        shots = []
    duration = data.get("duration")
    parsed = []
    seen_ids = set()
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            issues.append(("shape", f"第 {index + 1} 個鏡頭不是物件"))
            continue
        label = str(shot.get("id") or index + 1)
        if label in seen_ids:
            issues.append(("duplicate-id", f"鏡頭 {label} 的 id 重複"))
        seen_ids.add(label)
        try:
            start = float(shot.get("start"))
            end = float(shot.get("end"))
        except (TypeError, ValueError):
            issues.append(("time", f"鏡頭 {label} 的起迄不是數字"))
            continue
        if end <= start:
            issues.append(("time", f"鏡頭 {label} 的結束沒有晚於開始"))
            continue
        on_screen = str(shot.get("on_screen") or "")
        spoken = str(shot.get("spoken") or "")
        width = display_width(on_screen) if on_screen else 0
        if width > mobile:
            issues.append((
                "wide-text",
                f"鏡頭 {label} 的畫面字顯示寬度 {width}，超過這個市場的可編輯預設 {mobile}",
            ))
        need = spoken_seconds(spoken)
        if spoken and need > (end - start) + 0.15:
            issues.append((
                "cramped",
                f"鏡頭 {label} 的口播粗估 {need:.2f} 秒，長於鏡頭 {end - start:.2f} 秒。這不是完播預測",
            ))
        parsed.append({"id": label, "start": start, "end": end, "on_screen": on_screen, "spoken": spoken})
    parsed.sort(key=lambda item: (item["start"], item["end"]))
    if parsed and parsed[0]["start"] > 0.05:
        issues.append(("late-start", "第一個鏡頭沒有從 0 秒附近開始"))
    for index in range(1, len(parsed)):
        gap = parsed[index]["start"] - parsed[index - 1]["end"]
        if gap < -0.001:
            issues.append(("overlap", f"鏡頭 {parsed[index - 1]['id']} 和 {parsed[index]['id']} 時間重疊"))
        elif gap > GAP_SECONDS:
            issues.append(("gap", f"鏡頭 {parsed[index - 1]['id']} 之後空了 {gap:.2f} 秒。這不是字幕空檔清單"))
    if isinstance(duration, (int, float)):
        if parsed and parsed[-1]["end"] > float(duration) + 0.05:
            issues.append(("overrun", "最後一個鏡頭超過宣告的總長"))
        if parsed and float(duration) - parsed[-1]["end"] > GAP_SECONDS:
            issues.append(("uncovered", "宣告的總長尾端沒有鏡頭"))
    blob = "\n".join(item["on_screen"] + "\n" + item["spoken"] for item in parsed)
    return {
        "shots": len(parsed),
        "market": profile["id"],
        "locale": profile["locale"],
        "issues": issues,
        "term_flags": flag_terms(blob, profile["id"]),
    }


def main() -> None:
    try:
        market, args = pop_market(sys.argv[1:])
        out, args = pop_flag(args, "--out")
        overwrite = "--overwrite" in args
        args = has_flag(args, "--overwrite")
        as_json = "--json" in args
        args = has_flag(args, "--json")
        files = [item for item in args if not item.startswith("--")]
        if not files:
            print(__doc__)
            sys.exit(1)
        report = check(load_json(files[0]), market)
    except MarketError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except IoError as exc:
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
    print(f"\n  {report['shots']} 個鏡頭  {report['locale']}\n")
    for item in report["issues"]:
        print(f"    x  {item['code']:<12} {item['message']}")
    if not report["issues"]:
        print("    時間和畫面字寬度沒有標出問題。")
    if report["term_flags"]:
        print(f"    用詞標示 {len(report['term_flags'])} 則，原句沒有改。")
    print("  這是時間表檢查，不是觀看預測。\n")


if __name__ == "__main__":
    main()
