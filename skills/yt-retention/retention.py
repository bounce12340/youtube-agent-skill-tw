#!/usr/bin/env python3
# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""讀觀看停留 CSV，分開開頭流失、陡降和中段下滑。

    python3 retention.py retention.csv --duration 45
    python3 retention.py retention.csv --duration 45 --transcript transcript.srt
    python3 retention.py retention.csv --json --axis seconds

檔案來自你自己匯出的報表。這個工具只讀本機 CSV，不上網，也不會登入任何後台。

短影音（時長 180 秒以內，或沒給時長）把開頭窗口放在前 3 秒。
長片（時長超過 180 秒）沿用前 30 秒。可用 --hook-seconds 覆寫。

橫軸若是百分比又沒給時長，無法把「3 秒」對準格子，只會用前 5% 當近似，並在結果裡寫明。
有字幕時，陡降旁邊會附上當時的句子。曲線不能預測下一支片。
"""
from __future__ import annotations

import csv
import json
import os
import sys

_EDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-edit")
if _EDIT not in sys.path:
    sys.path.insert(0, _EDIT)


def load_csv(path: str) -> tuple[list[tuple[float, float]], str | None]:
    rows: list[tuple[float, float]] = []
    axis_hint = None
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        for index, raw in enumerate(reader):
            if not raw or not any(cell.strip() for cell in raw):
                continue
            nums: list[float | None] = []
            text_cells = []
            for cell in raw:
                cleaned = cell.strip().replace("%", "").replace("％", "").replace(",", "")
                try:
                    nums.append(float(cleaned))
                except ValueError:
                    nums.append(None)
                    if cell.strip():
                        text_cells.append(cell.strip().lower())
            if text_cells and index == 0:
                blob = " ".join(text_cells)
                if any(word in blob for word in ("second", "秒", "elapsed", "時間軸", "timestamp")):
                    axis_hint = "seconds"
                elif any(word in blob for word in ("%", "％", "percent", "百分比", "位置", "proportion")):
                    axis_hint = "percent"
                continue
            values = [num for num in nums if num is not None]
            if len(values) >= 2:
                rows.append((values[0], values[1]))
    return rows, axis_hint


def detect_axis(rows: list[tuple[float, float]], hint: str | None, duration: float | None, explicit: str | None) -> str:
    if explicit in {"percent", "seconds"}:
        return explicit
    if hint in {"percent", "seconds"}:
        return hint
    last = rows[-1][0]
    if last > 100.5:
        return "seconds"
    if duration is not None:
        if abs(last - duration) <= max(1.5, duration * 0.02) and abs(last - 100) > 5:
            return "seconds"
        if 99 <= last <= 100.5 and abs(duration - last) > 5:
            return "percent"
    if 95 <= last <= 100.5:
        return "percent"
    return "seconds"


def analyze(
    rows: list[tuple[float, float]],
    duration: float | None = None,
    hook_seconds: float | None = None,
    axis: str | None = None,
    axis_hint: str | None = None,
    cues: list[tuple[float, float, str]] | None = None,
) -> dict:
    if len(rows) < 8:
        raise ValueError("至少需要 8 個資料點")
    xs = [row[0] for row in rows]
    ys = [row[1] for row in rows]
    axis_name = detect_axis(rows, axis_hint, duration, axis)
    if hook_seconds is not None:
        window = hook_seconds
        window_mode = "custom"
    elif duration is not None and duration > 180:
        window = 30.0
        window_mode = "long"
    else:
        window = 3.0
        window_mode = "short"
    if axis_name == "percent":
        if duration:
            cutoff = window / duration * 100
            cutoff_mode = "seconds-on-percent"
        else:
            cutoff = 5.0
            cutoff_mode = "percent-unknown"
            window_mode = "percent-unknown"
    else:
        cutoff = window
        cutoff_mode = "seconds"

    def at_seconds(pos: float) -> float | None:
        if axis_name == "seconds":
            return pos
        if duration:
            return pos / 100.0 * duration
        return None

    start = ys[0] or 100.0
    in_window = [y for x, y in rows if x <= cutoff + 1e-9]
    hook_end = min(in_window) if in_window else start
    hook_leak = start - hook_end
    drops = []
    for index in range(1, len(rows)):
        lost = ys[index - 1] - ys[index]
        span = xs[index] - xs[index - 1] or 1
        drops.append((lost / span, xs[index - 1], xs[index], lost))
    drops.sort(reverse=True)
    cliffs = []
    for _rate, left, right, lost in drops[:5]:
        if lost <= 0.8:
            continue
        cliffs.append({
            "from": round(left, 2),
            "to": round(right, 2),
            "lost": round(lost, 2),
            "at_seconds": None if at_seconds(left) is None else round(at_seconds(left), 1),
        })
    middle = [lost for _rate, left, _right, lost in drops if left > cutoff]
    slide = sum(middle) / len(middle) if middle else 0
    said = {}
    if cues:
        for cliff in cliffs:
            if cliff["at_seconds"] is None:
                continue
            stamp = cliff["at_seconds"]
            near = [cue[2].replace("\n", " ") for cue in cues if cue[0] <= stamp + 4 and cue[1] >= stamp - 4]
            if near:
                said[str(cliff["from"])] = " ".join(near)[:140]
    if hook_leak < 25:
        verdict = "healthy"
    elif hook_leak < 40:
        verdict = "leaking"
    else:
        verdict = "severe"
    return {
        "points": len(rows),
        "axis": axis_name,
        "hook_window_seconds": None if window_mode == "percent-unknown" else window,
        "hook_window_mode": window_mode,
        "cutoff": round(cutoff, 3),
        "cutoff_mode": cutoff_mode,
        "start": start,
        "hook_leak": round(hook_leak, 2),
        "hook_verdict": verdict,
        "end": ys[-1],
        "cliffs": cliffs,
        "slide_per_unit": round(slide, 3),
        "said": said,
    }


def _flag(args: list[str], name: str) -> str | None:
    if name not in args:
        return None
    return args[args.index(name) + 1]


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [item for item in args if item != "--json"]
    duration = float(_flag(args, "--duration")) if _flag(args, "--duration") else None
    hook_seconds = float(_flag(args, "--hook-seconds")) if _flag(args, "--hook-seconds") else None
    axis = _flag(args, "--axis")
    transcript = _flag(args, "--transcript")
    skip = {duration and str(duration), hook_seconds and str(hook_seconds), axis, transcript}
    files = [
        item for item in args
        if not item.startswith("--") and item not in skip and not _is_number(item)
    ]
    if not files or not os.path.exists(files[0]):
        print(__doc__)
        sys.exit(1)
    rows, hint = load_csv(files[0])
    cues = None
    if transcript:
        if not os.path.exists(transcript):
            print("找不到字幕檔")
            sys.exit(1)
        from deadair import load as load_cues
        cues = load_cues(transcript)
    try:
        report = analyze(rows, duration, hook_seconds, axis, hint, cues)
    except ValueError as exc:
        print(str(exc))
        sys.exit(1)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print(f"\n  {os.path.basename(files[0])}  {report['points']} 點  {report['start']:.1f}% -> {report['end']:.1f}%")
    print(f"  橫軸 {report['axis']}，開頭窗口 {report['hook_window_mode']}，切點 {report['cutoff']}\n")
    labels = {"healthy": "還好", "leaking": "在漏", "severe": "流失很大"}
    print(f"  開頭流失  {report['hook_leak']:.1f}%  [{labels[report['hook_verdict']]}]")
    if report["hook_window_mode"] == "short":
        print("  短影音看的是前 3 秒。先改第一句，再動後面的剪輯。")
    elif report["hook_window_mode"] == "long":
        print("  這支超過 3 分鐘，開頭窗口用前 30 秒。")
    else:
        print("  百分比橫軸但沒有時長，無法對準 3 秒，暫用前 5%。請補 --duration。")
    print("\n  陡降      人真正離開的那幾格")
    if not report["cliffs"]:
        print("    沒有單格超過 0.8% 的陡降，流失是中段慢慢掉的")
    for cliff in report["cliffs"]:
        where = f"{cliff['at_seconds']:.0f} 秒" if cliff["at_seconds"] is not None else str(cliff["from"])
        quote = report["said"].get(str(cliff["from"]), "")
        extra = f"  「{quote}」" if quote else ""
        print(f"    -{cliff['lost']:5.1f}%  在 {where:>8}{extra}")
    print(f"\n  中段下滑  每單位約 {report['slide_per_unit']:.3f}%")
    print("  平緩下滑通常是節奏。先剪中段，不是整支重寫。")
    print("  這些數字描述這一支已發生的停留，不能預測下一支。\n")


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    main()
