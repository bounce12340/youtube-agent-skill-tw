#!/usr/bin/env python3
# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""從有時間碼的字幕做剪輯清單。只印清單，不改影片檔。

    python3 deadair.py transcript.srt
    python3 deadair.py transcript.vtt --floor 0.30 --json
    python3 deadair.py whisper.json

找三件事：
  DEAD    兩句之間的空檔長過門檻。從中間剪，兩邊各留半個門檻當氣口。
  FILLER  整格字幕都是口頭禪，例如「嗯」「那個」「就是」「然後」，或 um、you know。
  REPEAT  同一句重拍。對的是上一格真正的話，不是中間隔著的「嗯」。

雙語字幕（英文一行、繁中一行，或同一格裡兩種字）只要有一行是內容，就不會整格當口頭禪。
預設門檻 0.45 秒，避免把自然換氣剪成喘。短影音若要更緊，再加 --floor 0.30。

支援 .srt、.vtt、Whisper 的 segments JSON。不上網。
"""
from __future__ import annotations

import json
import os
import re
import sys

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from zhtext import clean_caption, is_filler_cue, opening_keys, script_mix  # noqa: E402


def parse_ts(raw: str) -> float:
    text = raw.strip().replace(",", ".")
    parts = text.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def _skip_block(line: str) -> bool:
    head = line.strip().upper()
    return head.startswith(("NOTE", "STYLE", "REGION"))


def load(path: str) -> list[tuple[float, float, str]]:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        raw = fh.read()
    if path.endswith(".json"):
        data = json.loads(raw)
        if isinstance(data, dict):
            segments = data.get("segments", [])
        elif isinstance(data, list):
            segments = data
        else:
            segments = []
        cues = []
        for seg in segments:
            text = clean_caption(str(seg.get("text") or ""))
            if text:
                cues.append((float(seg["start"]), float(seg["end"]), text))
        return cues
    cues: list[list] = []
    current = None
    skipping = False
    for line in raw.splitlines():
        if _skip_block(line):
            skipping = True
            current = None
            continue
        if skipping:
            if not line.strip():
                skipping = False
            continue
        stripped = line.strip()
        if stripped.upper().startswith(("WEBVTT", "KIND:", "LANGUAGE:", "X-TIMESTAMP-MAP")):
            continue
        match = re.match(r"\s*(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)", line)
        if match:
            current = [parse_ts(match.group(1)), parse_ts(match.group(2)), []]
            cues.append(current)
            continue
        if current is not None and stripped and not stripped.isdigit():
            cleaned = clean_caption(stripped)
            if cleaned:
                current[2].append(cleaned)
    return [(start, end, "\n".join(lines)) for start, end, lines in cues if lines]


def build_cuts(cues: list[tuple[float, float, str]], floor: float) -> list[dict]:
    cuts = []
    for index, (start, end, text) in enumerate(cues):
        if is_filler_cue(text):
            cuts.append({
                "kind": "FILLER",
                "start": round(start, 3),
                "end": round(end, 3),
                "why": text.replace("\n", " / ")[:80],
                "mix": script_mix(text),
            })
        if index:
            gap = start - cues[index - 1][1]
            if gap > floor:
                keep = floor / 2
                cuts.append({
                    "kind": "DEAD",
                    "start": round(cues[index - 1][1] + keep, 3),
                    "end": round(start - keep, 3),
                    "why": f"{gap:.2f} 秒空檔",
                    "mix": "gap",
                })
        if text.strip() and not is_filler_cue(text):
            previous = index - 1
            while previous >= 0 and (is_filler_cue(cues[previous][2]) or not cues[previous][2].strip()):
                previous -= 1
            if previous >= 0:
                now_keys = opening_keys(text)
                old_keys = opening_keys(cues[previous][2])
                shared = now_keys & old_keys
                if shared:
                    shown = next(iter(shared))[1]
                    if isinstance(shown, tuple):
                        shown = " ".join(shown)
                    cuts.append({
                        "kind": "REPEAT",
                        "start": round(cues[previous][0], 3),
                        "end": round(cues[previous][1], 3),
                        "why": f"重拍，開頭同為「{shown}」",
                        "mix": script_mix(text),
                    })
    return [cut for cut in cuts if cut["end"] > cut["start"]]


def analyze(path: str, floor: float = 0.45) -> dict:
    cues = load(path)
    if not cues:
        raise ValueError("沒有讀到字幕。需要 srt、vtt 或 Whisper segments JSON。")
    duration = cues[-1][1]
    cuts = build_cuts(cues, floor)
    removed = sum(cut["end"] - cut["start"] for cut in cuts)
    return {
        "source": os.path.basename(path),
        "duration": round(duration, 3),
        "cues": len(cues),
        "floor": floor,
        "cuts": cuts,
        "removed": round(removed, 3),
        "out": round(duration - removed, 3),
    }


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [item for item in args if item != "--json"]
    floor = float(args[args.index("--floor") + 1]) if "--floor" in args else 0.45
    files = [item for item in args if not item.startswith("--") and not re.match(r"^[\d.]+$", item)]
    if not files or not os.path.exists(files[0]):
        print(__doc__)
        sys.exit(1)
    try:
        report = analyze(files[0], floor)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc))
        sys.exit(1)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print(f"\n  {report['source']}  輸入 {report['duration']:.2f} 秒，{report['cues']} 格，空檔門檻 {floor} 秒\n")
    for cut in report["cuts"]:
        span = cut["end"] - cut["start"]
        print(f"    {cut['kind']:<7} {cut['start']:8.2f} -> {cut['end']:8.2f}  {span:5.2f} 秒  {cut['why']}")
    duration = report["duration"] or 1
    removed = report["removed"]
    print(
        f"\n  {len(report['cuts'])} 個剪點，去掉 {removed:.2f} 秒，"
        f"大約剩 {report['out']:.2f} 秒（口播縮短 {removed / duration * 100:.1f}%）"
    )
    print("  這份清單不改影片。若中間有無聲示範，底部秒數會偏短，請對一下畫面。\n")


if __name__ == "__main__":
    main()
