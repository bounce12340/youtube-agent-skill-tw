#!/usr/bin/env python3
# Original checker. video-production-skills was inspected and not copied.
"""檢查混音計畫裡的淡入淡出、增益，以及人聲底下的配樂有沒有讓位。

    python3 mixcheck.py mix.json
    python3 mixcheck.py mix.json --duck-gap 6 --json

讀的是你寫的計畫，不是音訊檔。沒有 peak_dbfs 就不會假裝已經檢查過削波。
預設：配樂在和人聲重疊時，增益至少比人聲低 6 dB，或自行宣告 duck_db 至少 6。
這是可改的技術預設，不是聽感評分，也不是某個帳號的混音習慣。
"""
from __future__ import annotations

import json
import os
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from markets import MarketError, get_market, pop_market  # noqa: E402
from vpio import IoError, has_flag, load_json, pop_flag, public_issues, write_json  # noqa: E402

ROLES = {"voice", "music", "sfx", "other"}
DUCK_GAP = 6.0
NEAR_CLIP = -1.0


def _overlap(left: dict, right: dict) -> bool:
    return left["start"] < right["end"] and right["start"] < left["end"]


def check(data: dict, market: str = "tw", duck_gap: float = DUCK_GAP) -> dict:
    profile = get_market(market)
    clips = data.get("clips")
    issues: list[tuple[str, str]] = []
    if not isinstance(clips, list) or not clips:
        issues.append(("empty", "混音計畫沒有音軌片段"))
        clips = []
    parsed = []
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            issues.append(("shape", f"第 {index + 1} 段不是物件"))
            continue
        label = str(clip.get("id") or index + 1)
        role = str(clip.get("role") or "")
        if role not in ROLES:
            issues.append(("role", f"片段 {label} 的 role 要是 voice、music、sfx 或 other"))
            continue
        try:
            start = float(clip.get("start"))
            end = float(clip.get("end"))
            gain = float(clip.get("gain_db"))
            fade_in = float(clip.get("fade_in") or 0)
            fade_out = float(clip.get("fade_out") or 0)
        except (TypeError, ValueError):
            issues.append(("number", f"片段 {label} 的時間或增益不是數字"))
            continue
        if end <= start:
            issues.append(("time", f"片段 {label} 的結束沒有晚於開始"))
            continue
        span = end - start
        if fade_in < 0 or fade_out < 0:
            issues.append(("fade", f"片段 {label} 的淡入或淡出是負的"))
        elif fade_in + fade_out > span + 1e-6:
            issues.append(("fade-overrun", f"片段 {label} 的淡入加淡出長過片段本身"))
        elif role in {"music", "sfx"} and fade_in == 0 and fade_out == 0:
            issues.append(("hard-edge", f"片段 {label} 是 {role}，頭尾都沒有淡入淡出"))
        if gain > 0:
            issues.append(("clip-risk", f"片段 {label} 的增益是 {gain} dB，高過 0 就有削波風險"))
        peak = clip.get("peak_dbfs")
        if peak is None:
            issues.append(("peak-unknown", f"片段 {label} 沒有 peak_dbfs，削波沒有被量過"))
        else:
            try:
                peak_value = float(peak)
            except (TypeError, ValueError):
                issues.append(("number", f"片段 {label} 的 peak_dbfs 不是數字"))
                peak_value = None
            if peak_value is not None and peak_value > NEAR_CLIP:
                issues.append(("near-clip", f"片段 {label} 的峰值 {peak_value} dBFS，靠近滿刻度"))
        duck = clip.get("duck_db")
        duck_value = None
        if duck is not None:
            try:
                duck_value = float(duck)
            except (TypeError, ValueError):
                issues.append(("number", f"片段 {label} 的 duck_db 不是數字"))
        parsed.append({
            "id": label,
            "role": role,
            "start": start,
            "end": end,
            "gain_db": gain,
            "duck_db": duck_value,
        })
    voices = [clip for clip in parsed if clip["role"] == "voice"]
    if parsed and not voices:
        issues.append(("no-voice", "計畫裡沒有人聲。若這支片本來就沒有人聲，可忽略"))
    for music in parsed:
        if music["role"] != "music":
            continue
        for voice in voices:
            if not _overlap(music, voice):
                continue
            quiet = music["gain_db"] <= voice["gain_db"] - duck_gap
            declared = music["duck_db"] is not None and music["duck_db"] >= duck_gap
            if not (quiet or declared):
                issues.append((
                    "duck-shallow",
                    f"配樂 {music['id']} 和人聲 {voice['id']} 重疊，"
                    f"增益沒有低過 {duck_gap} dB，也沒有宣告足夠的 duck_db",
                ))
    return {
        "clips": len(parsed),
        "duck_gap": duck_gap,
        "market": profile["id"],
        "locale": profile["locale"],
        "issues": issues,
        "term_flags": [],
    }


def main() -> None:
    try:
        market, args = pop_market(sys.argv[1:])
        out, args = pop_flag(args, "--out")
        gap_text, args = pop_flag(args, "--duck-gap")
        overwrite = "--overwrite" in args
        args = has_flag(args, "--overwrite")
        as_json = "--json" in args
        args = has_flag(args, "--json")
        files = [item for item in args if not item.startswith("--")]
        if not files:
            print(__doc__)
            sys.exit(1)
        gap = float(gap_text) if gap_text is not None else DUCK_GAP
        report = check(load_json(files[0]), market, gap)
    except MarketError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except (IoError, ValueError) as exc:
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
    print(f"\n  {report['clips']} 段  讓位門檻 {report['duck_gap']} dB  {report['locale']}\n")
    for item in report["issues"]:
        print(f"    x  {item['code']:<14} {item['message']}")
    if not report["issues"]:
        print("    計畫裡的淡入淡出、增益和讓位沒有標出問題。")
    print("  這沒有聽過音訊，也不能代替耳朵。\n")


if __name__ == "__main__":
    main()
