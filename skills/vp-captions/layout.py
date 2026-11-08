#!/usr/bin/env python3
# Original checker. video-production-skills was inspected and not copied.
"""檢查字幕每一格的行數、顯示寬度和停留時間。不產生剪輯點。

    python3 layout.py captions.srt
    python3 layout.py captions.srt --market hk --json

預設一行不要超過該市場的手機寬度預設，一格不要超過兩行。
這是可讀性的可編輯預設，不是平台字數，也不是完播模型。
口播粗估仍是 4.5 字／秒，五個市場相同。
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
from vpio import IoError, has_flag, pop_flag, public_issues, write_json  # noqa: E402
from zhtext import display_width, spoken_seconds  # noqa: E402

MAX_LINES = 2


def check(cues: list[tuple[float, float, str]], market: str = "tw", max_lines: int = MAX_LINES) -> dict:
    profile = get_market(market)
    mobile = profile["layout"]["mobile_width"]
    issues: list[tuple[str, str]] = []
    if not cues:
        issues.append(("empty", "沒有讀到字幕"))
    ordered = sorted(cues, key=lambda item: (item[0], item[1]))
    previous_end = None
    for index, (start, end, text) in enumerate(ordered, start=1):
        if end <= start:
            issues.append(("time", f"第 {index} 格的結束沒有晚於開始"))
            continue
        if previous_end is not None and start < previous_end - 0.001:
            issues.append(("overlap", f"第 {index} 格和上一格時間重疊"))
        previous_end = end
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) > max_lines:
            issues.append(("lines", f"第 {index} 格有 {len(lines)} 行，可編輯預設是 {max_lines} 行"))
        for line in lines:
            width = display_width(line)
            if width > mobile:
                issues.append((
                    "wide-line",
                    f"第 {index} 格有一行顯示寬度 {width}，超過這個市場的可編輯預設 {mobile}",
                ))
        need = spoken_seconds(text)
        span = end - start
        if need > 0 and span + 0.05 < need * 0.8:
            issues.append((
                "too-fast",
                f"第 {index} 格只有 {span:.2f} 秒，口播粗估要 {need:.2f} 秒。這是讀不讀得完，不是完播預測",
            ))
    blob = "\n".join(text for _start, _end, text in ordered)
    return {
        "cues": len(ordered),
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
        if not files or not os.path.exists(files[0]):
            print(__doc__)
            sys.exit(1)
        from deadair import load

        report = check(load(files[0]), market)
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
    print(f"\n  {report['cues']} 格字幕  {report['locale']}\n")
    for item in report["issues"]:
        print(f"    x  {item['code']:<12} {item['message']}")
    if not report["issues"]:
        print("    行數、寬度和停留沒有標出問題。")
    if report["term_flags"]:
        print(f"    用詞標示 {len(report['term_flags'])} 則，字幕原文沒有改。")
    print("  這不是口頭禪剪輯清單。空檔和重拍仍用 deadair.py。\n")


if __name__ == "__main__":
    main()
