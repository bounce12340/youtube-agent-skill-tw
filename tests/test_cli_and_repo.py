import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a2feb2104981a375ffd4f87ee04f4f5344ac43c6"
PY = sys.executable

SCAN_DIRS = ["skills", "templates", "samples", "tests"]
SCAN_FILES = ["README.md", "LICENSE", "upstream.json"]
BANNED = ("\u2014", "\u6578\u64da", "\u7b97\u529b", "\u8cfd\u9053", "\u5377")
PRIVATE = ("Josh", "bounce12340", "/home/", "/Users/", "AKIA", "api_key", "secret_key")
NETWORK = {"urllib", "urllib.request", "requests", "httpx", "socket", "http.client", "aiohttp"}


def scanned_files():
    files = [ROOT / name for name in SCAN_FILES]
    for folder in SCAN_DIRS:
        for path in (ROOT / folder).rglob("*"):
            if path.name == "test_cli_and_repo.py":
                continue
            if path.is_file() and path.suffix.lower() in {".py", ".md", ".json", ".txt", ".csv", ".vtt", ".srt"}:
                files.append(path)
    return files


class CliTests(unittest.TestCase):
    def run_tool(self, args):
        return subprocess.run(
            [PY, *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_sample_commands(self):
        commands = [
            ["skills/yt-script/hookscore.py", "samples/hooks.txt", "--json"],
            ["skills/yt-package/title.py", "samples/titles.txt", "--json"],
            ["skills/yt-package/title.py", "--title", "30 秒講完字幕", "--cover", "別自介", "--json"],
            ["skills/yt-edit/deadair.py", "samples/transcript_edit.srt", "--json"],
            ["skills/yt-edit/deadair.py", "samples/transcript_bilingual.vtt", "--json"],
            ["skills/yt-edit/deadair.py", "samples/whisper_zh.json", "--json"],
            ["skills/yt-chapters/chapters.py", "samples/transcript_chapters.srt", "--json"],
            ["skills/yt-retention/retention.py", "samples/retention_short_seconds.csv", "--json"],
            ["skills/yt-retention/retention.py", "samples/retention_short_percent.csv", "--duration", "45", "--json"],
            ["skills/yt-retention/retention.py", "samples/retention_long_percent.csv", "--duration", "600", "--json"],
            ["skills/yt-viral/swipe.py", "samples/collected.json", "--min", "2.0", "--json"],
        ]
        for command in commands:
            result = self.run_tool(command)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            json.loads(result.stdout)

    def test_missing_file_exits(self):
        result = self.run_tool(["skills/yt-edit/deadair.py", "samples/missing.srt"])
        self.assertEqual(result.returncode, 1)


class RepoTests(unittest.TestCase):
    def test_upstream_pin_and_license(self):
        meta = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["commit"], COMMIT)
        self.assertFalse(meta["official"])
        self.assertEqual(meta["author"], "Jake Schincariol")
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        hooks = (ROOT / "skills/yt-script/hooks.json").read_text(encoding="utf-8")
        for blob in (license_text, readme, hooks):
            self.assertIn(COMMIT, blob)
            self.assertIn("Jake Schincariol", blob)
        self.assertIn("Copyright (c) 2026 Jake Schincariol", license_text)
        self.assertIn("MIT License", license_text)
        self.assertIn("不是官方", readme)
        self.assertNotIn("Install this skill", readme)

    def test_no_banned_terms_emdash_or_private_data(self):
        for path in scanned_files():
            text = path.read_text(encoding="utf-8")
            for needle in BANNED + PRIVATE:
                self.assertNotIn(needle, text, f"{path} contains {needle!r}")

    def test_tools_do_not_import_network(self):
        for path in (ROOT / "skills").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                self.assertFalse(set(names) & NETWORK, path)

    def test_skill_count_and_traditional_gate(self):
        skills = list((ROOT / "skills").glob("yt-*/SKILL.md"))
        self.assertEqual(len(skills), 11)
        for path in skills:
            text = path.read_text(encoding="utf-8")
            self.assertIn("要發出，還是再改？", text)
            self.assertIn("不是 Jake Schincariol 的官方專案", text)


if __name__ == "__main__":
    unittest.main()
