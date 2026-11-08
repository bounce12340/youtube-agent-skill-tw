# Original checkers for this adaptation. Not copied from video-production-skills.
# That repository has no license. See upstream-video.json.
"""本機報告的讀寫。不上網，不覆寫已有檔，除非明確加上 --overwrite。"""
from __future__ import annotations

import json
import os
from pathlib import Path


class IoError(ValueError):
    pass


def load_json(path: str) -> dict:
    target = Path(path)
    if not target.is_file():
        raise IoError(f"找不到檔案：{path}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IoError(f"JSON 讀不到：{exc}") from exc
    if not isinstance(data, dict):
        raise IoError("最外層要是物件")
    return data


def pop_flag(args: list[str], name: str) -> tuple[str | None, list[str]]:
    kept: list[str] = []
    value = None
    index = 0
    while index < len(args):
        if args[index] == name:
            if index + 1 >= len(args):
                raise IoError(f"{name} 後面要接值")
            value = args[index + 1]
            index += 2
            continue
        kept.append(args[index])
        index += 1
    return value, kept


def has_flag(args: list[str], name: str) -> list[str]:
    return [item for item in args if item != name]


def write_json(path: str, payload: dict, overwrite: bool = False) -> None:
    """寫報告。已存在就停，避免蓋掉使用者的檔。"""
    target = Path(path)
    if target.suffix.lower() != ".json":
        raise IoError("報告只能寫成 .json")
    if any(part == ".." for part in target.parts):
        raise IoError("報告路徑不能含 ..")
    if not target.parent.exists():
        raise IoError("報告所在的目錄不存在")
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    flags = os.O_CREAT | os.O_WRONLY
    if overwrite:
        flags |= os.O_TRUNC
    else:
        flags |= os.O_EXCL
    try:
        fd = os.open(target, flags, 0o644)
    except FileExistsError as exc:
        raise IoError("檔案已存在。要覆寫請加上 --overwrite。") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def public_issues(issues: list[tuple[str, str]]) -> list[dict]:
    return [{"code": code, "message": message} for code, message in issues]
