#!/usr/bin/env python3
# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""從字幕草稿長片章節。短影音預設不需要章節。

    python3 chapters.py transcript.srt
    python3 chapters.py transcript.srt --target 6 --json

YouTube 自己的規則：第一條必須是 0:00，至少三條，每一條至少 10 秒。
不合規則的清單貼進描述也不會變成章節，所以這裡先檢查。

分段看兩件事：你真正停下來的空檔，以及空檔前後用詞差多少。
中文沒有空格，用的是常用字過濾後的二字組，不是斷詞器。
標題是草稿，貼上前要改成你會講的話。這個工具不上網。
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-edit"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))

from deadair import load  # noqa: E402
from zhtext import content_grams, cjk_chars, display_width, truncate_display  # noqa: E402

MIN_SECONDS = 10.0


def mmss(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def draft_title(text: str) -> str:
    clause = re.split(r"[。！？!?；;\n]", text, maxsplit=1)[0].strip()
    for prefix in ("然後", "就是", "那個", "所以", "其實"):
        if clause.startswith(prefix):
            clause = clause[len(prefix):].lstrip(" ，,、")
    clause = truncate_display(clause, 24)
    if display_width(clause) >= 8 and len(cjk_chars(clause)) >= 4:
        return clause
    grams = [gram for gram in content_grams(text) if len(gram) == 2]
    grams.sort(key=lambda gram: (-text.count(gram), gram))
    if grams:
        return "、".join(grams[:2])
    words = [word for word in re.findall(r"[A-Za-z]{4,}", text)]
    if words:
        return " ".join(words[:3])
    return "未命名"


def build_chapters(cues: list[tuple[float, float, str]], target: int = 7) -> dict:
    if len(cues) < 6:
        return {"valid": False, "reason": "字幕少於 6 格，不夠分段", "chapters": []}
    duration = cues[-1][1]
    if duration < MIN_SECONDS * 3:
        return {
            "valid": False,
            "reason": "總長不到 30 秒。章節是長片用的，3 分鐘內的短影音可以略過",
            "chapters": [],
        }
    candidates = []
    for index in range(1, len(cues)):
        gap = cues[index][0] - cues[index - 1][1]
        before = " ".join(cue[2] for cue in cues[max(0, index - 12):index])
        after = " ".join(cue[2] for cue in cues[index:index + 12])
        left, right = content_grams(before), content_grams(after)
        shift = 1 - (len(left & right) / len(left | right)) if (left or right) else 0
        candidates.append((gap * 1.6 + shift * 3.2, cues[index][0], index))
    candidates.sort(reverse=True)
    picked = [0.0]
    for _score, stamp, _index in candidates:
        if len(picked) >= target:
            break
        if all(abs(stamp - kept) >= MIN_SECONDS for kept in picked) and duration - stamp >= MIN_SECONDS:
            picked.append(stamp)
    picked.sort()
    chapters = []
    for index, stamp in enumerate(picked):
        end = picked[index + 1] if index + 1 < len(picked) else duration
        text = " ".join(cue[2] for cue in cues if cue[0] >= stamp - 0.05 and cue[1] <= end + 0.05)
        chapters.append({
            "start": round(stamp, 2),
            "label": mmss(stamp),
            "draft_title": draft_title(text),
            "seconds": round(end - stamp, 2),
        })
    valid = (
        len(chapters) >= 3
        and chapters[0]["start"] == 0
        and all(item["seconds"] >= MIN_SECONDS for item in chapters)
    )
    reason = "" if valid else "不合 YouTube 規則：要有 3 條以上、第一條 0:00、每條至少 10 秒"
    return {"valid": valid, "reason": reason, "chapters": chapters}


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    args = [item for item in args if item != "--json"]
    target = int(args[args.index("--target") + 1]) if "--target" in args else 7
    files = [item for item in args if not item.startswith("--") and not item.isdigit()]
    if not files or not os.path.exists(files[0]):
        print(__doc__)
        sys.exit(1)
    cues = load(files[0])
    if len(cues) < 6:
        print("字幕少於 6 格，不夠分段")
        sys.exit(1)
    report = build_chapters(cues, target)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print()
    for chapter in report["chapters"]:
        print(f"  {chapter['label']} {chapter['draft_title']}")
    if report["valid"]:
        print(f"\n  {len(report['chapters'])} 條，符合 0:00、至少三條、每條至少 10 秒。")
    else:
        print(f"\n  {len(report['chapters'])} 條。{report['reason']}")
    print("  貼上前改掉每一行。這些是草稿，不是你的句子。短影音通常不需要章節。\n")


if __name__ == "__main__":
    main()
