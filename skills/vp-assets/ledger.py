#!/usr/bin/env python3
# Original checker. video-production-skills was inspected and not copied.
"""檢查素材清單有沒有來源和授權標籤。不判斷授權是否合法。

    python3 ledger.py assets.json
    python3 ledger.py assets.json --check-files --root . --json

授權標籤是你自己寫的字，例如 own、cc-by、licensed。空白才會被標出。
這個工具不上網，也不把檔案移走。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from markets import MarketError, get_market, pop_market  # noqa: E402
from vpio import IoError, has_flag, load_json, pop_flag, public_issues, write_json  # noqa: E402


def safe_relative(path: str) -> bool:
    if not path or any(char in path for char in "\n\r\x00"):
        return False
    if path.startswith(("/", "\\")):
        return False
    parts = Path(path).parts
    return ".." not in parts and parts != (".",)


def check(data: dict, market: str = "tw", root: str | None = None, check_files: bool = False) -> dict:
    profile = get_market(market)
    assets = data.get("assets")
    issues: list[tuple[str, str]] = []
    if not isinstance(assets, list) or not assets:
        issues.append(("empty", "素材清單是空的"))
        assets = []
    seen_ids = set()
    seen_paths = set()
    base = Path(root).resolve() if root else Path.cwd()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            issues.append(("shape", f"第 {index + 1} 筆不是物件"))
            continue
        label = str(asset.get("id") or index + 1)
        if label in seen_ids:
            issues.append(("duplicate-id", f"素材 {label} 的 id 重複"))
        seen_ids.add(label)
        path = str(asset.get("path") or "")
        if not safe_relative(path):
            issues.append(("path", f"素材 {label} 的路徑要是相對路徑，且不能含 .."))
        elif path in seen_paths:
            issues.append(("duplicate-path", f"路徑 {path} 出現超過一次"))
        else:
            seen_paths.add(path)
            if check_files:
                full = (base / path).resolve()
                if base not in full.parents and full != base:
                    issues.append(("path", f"素材 {label} 跑出 --root"))
                elif not full.is_file():
                    issues.append(("missing-file", f"找不到 {path}"))
        if not str(asset.get("source") or "").strip():
            issues.append(("source", f"素材 {label} 沒有寫來源"))
        if not str(asset.get("license_label") or "").strip():
            issues.append(("license-label", f"素材 {label} 沒有授權標籤。這不是法律結論，只是欄位空了"))
    return {
        "assets": len(seen_ids),
        "market": profile["id"],
        "locale": profile["locale"],
        "issues": issues,
        "term_flags": [],
    }


def main() -> None:
    try:
        market, args = pop_market(sys.argv[1:])
        out, args = pop_flag(args, "--out")
        root, args = pop_flag(args, "--root")
        overwrite = "--overwrite" in args
        check_files = "--check-files" in args
        args = has_flag(has_flag(args, "--overwrite"), "--check-files")
        as_json = "--json" in args
        args = has_flag(args, "--json")
        files = [item for item in args if not item.startswith("--")]
        if not files:
            print(__doc__)
            sys.exit(1)
        report = check(load_json(files[0]), market, root, check_files)
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
    print(f"\n  {report['assets']} 筆素材  {report['locale']}\n")
    for item in report["issues"]:
        print(f"    x  {item['code']:<16} {item['message']}")
    if not report["issues"]:
        print("    來源和授權標籤都有填。這仍不是法律許可。")
    print()


if __name__ == "__main__":
    main()
