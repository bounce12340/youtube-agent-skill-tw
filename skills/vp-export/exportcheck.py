#!/usr/bin/env python3
# Original checker. video-production-skills was inspected and not copied.
"""對一份輸出說明做技術檢查。預設不呼叫 ffprobe，也不渲染、不上傳。

    python3 exportcheck.py export.json --preset vertical --json
    python3 exportcheck.py --run-ffprobe clip.mp4 --preset vertical --json

內建 vertical 是 1080x1920、30 fps、雙聲道 48000 Hz。
horizontal 是 1920x1080，其餘相同。這是可改的技術預設，不是市場成效。
要用自己的數字，加 --target 指向一份 JSON。
沒有 peak_dbfs 時會標出「沒量過」，不會把它當成已通過。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from markets import MarketError, get_market, pop_market  # noqa: E402
from vpio import IoError, has_flag, load_json, pop_flag, public_issues, write_json  # noqa: E402

PRESETS = {
    "vertical": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "sample_rate": 48000,
        "channels": 2,
        "container": "mp4",
    },
    "horizontal": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "sample_rate": 48000,
        "channels": 2,
        "container": "mp4",
    },
}
NEAR_CLIP = -1.0


def _rate(text: str) -> float | None:
    if not text or text == "0/0":
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            denom = float(right)
            if denom == 0:
                return None
            return float(left) / denom
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def manifest_from_ffprobe(info: dict) -> dict:
    streams = info.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    form = info.get("format") or {}
    try:
        duration = float(form.get("duration"))
    except (TypeError, ValueError):
        duration = None
    names = str(form.get("format_name") or "")
    container = "mp4" if "mp4" in names else names.split(",")[0]
    out = {"container": container, "duration": duration, "video": {}, "audio": {}}
    if video:
        fps = _rate(str(video.get("avg_frame_rate") or "")) or _rate(str(video.get("r_frame_rate") or ""))
        out["video"] = {
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": fps,
            "codec": video.get("codec_name"),
        }
    if audio:
        try:
            rate = int(audio.get("sample_rate"))
        except (TypeError, ValueError):
            rate = None
        out["audio"] = {
            "sample_rate": rate,
            "channels": audio.get("channels"),
            "codec": audio.get("codec_name"),
        }
    return out


def run_ffprobe(path: str) -> dict:
    if shutil.which("ffprobe") is None:
        raise IoError("找不到 ffprobe。請改交已經存好的 JSON。這個工具不會安裝它。")
    target = Path(path)
    if "\x00" in str(target) or not target.is_file():
        raise IoError("找不到媒體檔")
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", "--", str(target)],
        check=False,
        capture_output=True,
        text=True,
        timeout=8,
        shell=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise IoError("ffprobe 沒有讀成這份檔")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise IoError("ffprobe 的輸出不是 JSON") from exc


def check(data: dict, target: dict, market: str = "tw", max_duration: float | None = None) -> dict:
    profile = get_market(market)
    issues: list[tuple[str, str]] = []
    video = data.get("video") if isinstance(data.get("video"), dict) else {}
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}
    try:
        width = int(video.get("width"))
        height = int(video.get("height"))
        fps = float(video.get("fps"))
        rate = int(audio.get("sample_rate"))
        channels = int(audio.get("channels"))
        duration = float(data.get("duration"))
    except (TypeError, ValueError):
        issues.append(("shape", "輸出說明缺了寬、高、fps、取樣率、聲道或時長"))
        width = height = rate = channels = None
        fps = duration = None
    if width is not None and (width != target["width"] or height != target["height"]):
        issues.append((
            "frame",
            f"畫面是 {width}x{height}，這份技術預設是 {target['width']}x{target['height']}",
        ))
    if fps is not None and abs(fps - float(target["fps"])) > 0.05:
        issues.append(("fps", f"fps 是 {fps}，這份技術預設是 {target['fps']}"))
    if rate is not None and rate != int(target["sample_rate"]):
        issues.append(("sample-rate", f"取樣率是 {rate}，這份技術預設是 {target['sample_rate']}"))
    if channels is not None and channels != int(target["channels"]):
        issues.append(("channels", f"聲道是 {channels}，這份技術預設是 {target['channels']}"))
    container = str(data.get("container") or "")
    wanted = str(target.get("container") or "")
    if wanted and container and wanted not in container:
        issues.append(("container", f"容器是 {container}，這份技術預設要含 {wanted}"))
    if duration is not None and duration <= 0:
        issues.append(("duration", "時長不是正數"))
    if duration is not None and max_duration is not None and duration > max_duration:
        issues.append(("long", f"時長 {duration} 秒，超過你給的 --max-duration {max_duration}"))
    peak = None if not isinstance(audio, dict) else audio.get("peak_dbfs")
    if peak is None:
        issues.append(("peak-unknown", "沒有 peak_dbfs，削波沒有被量過"))
    else:
        try:
            peak_value = float(peak)
        except (TypeError, ValueError):
            issues.append(("number", "peak_dbfs 不是數字"))
            peak_value = None
        if peak_value is not None and peak_value > NEAR_CLIP:
            issues.append(("near-clip", f"峰值 {peak_value} dBFS，靠近滿刻度"))
    return {
        "market": profile["id"],
        "locale": profile["locale"],
        "preset": target.get("name"),
        "issues": issues,
        "term_flags": [],
    }


def load_target(preset: str | None, path: str | None) -> dict:
    if path:
        data = load_json(path)
        data.setdefault("name", Path(path).stem)
        for key in ("width", "height", "fps", "sample_rate", "channels"):
            if key not in data:
                raise IoError(f"目標檔缺 {key}")
        return data
    name = preset or "vertical"
    if name not in PRESETS:
        raise IoError("預設只有 vertical 或 horizontal。其他數字請用 --target。")
    found = dict(PRESETS[name])
    found["name"] = name
    return found


def main() -> None:
    try:
        market, args = pop_market(sys.argv[1:])
        out, args = pop_flag(args, "--out")
        preset, args = pop_flag(args, "--preset")
        target_path, args = pop_flag(args, "--target")
        media, args = pop_flag(args, "--run-ffprobe")
        max_text, args = pop_flag(args, "--max-duration")
        overwrite = "--overwrite" in args
        args = has_flag(args, "--overwrite")
        as_json = "--json" in args
        args = has_flag(args, "--json")
        files = [item for item in args if not item.startswith("--")]
        if media:
            data = manifest_from_ffprobe(run_ffprobe(media))
        elif files:
            data = load_json(files[0])
        else:
            print(__doc__)
            sys.exit(1)
        target = load_target(preset, target_path)
        max_duration = float(max_text) if max_text is not None else None
        report = check(data, target, market, max_duration)
    except MarketError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except (IoError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ffprobe 超過 8 秒", file=sys.stderr)
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
    print(f"\n  技術預設 {report['preset']}  {report['locale']}\n")
    for item in report["issues"]:
        print(f"    x  {item['code']:<14} {item['message']}")
    if not report["issues"]:
        print("    和這份技術預設一致，峰值也沒有靠近滿刻度。")
    print("  沒有渲染，也沒有上傳。\n")


if __name__ == "__main__":
    main()
