import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"


def load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# deadair 必須先以這個模組名載入，chapters 才能 import。
load("deadair", "skills/yt-edit/deadair.py")
chapters = load("chapters", "skills/yt-chapters/chapters.py")
retention = load("retention", "skills/yt-retention/retention.py")
swipe = load("swipe", "skills/yt-viral/swipe.py")


class ChapterTests(unittest.TestCase):
    def test_long_sample_is_valid_youtube_chapters(self):
        cues = chapters.load(str(SAMPLES / "transcript_chapters.srt"))
        report = chapters.build_chapters(cues, target=7)
        self.assertTrue(report["valid"], report)
        self.assertGreaterEqual(len(report["chapters"]), 3)
        self.assertEqual(report["chapters"][0]["start"], 0)
        self.assertEqual(report["chapters"][0]["label"], "0:00")
        for chapter in report["chapters"]:
            self.assertGreaterEqual(chapter["seconds"], 10)
            self.assertTrue(chapter["draft_title"])

    def test_short_video_is_rejected(self):
        cues = [(index * 1.5, index * 1.5 + 1.2, "封面標題字幕留言發佈短影音") for index in range(8)]
        report = chapters.build_chapters(cues)
        self.assertFalse(report["valid"])
        self.assertIn("短影音", report["reason"])


class RetentionTests(unittest.TestCase):
    def test_short_seconds_use_three_second_hook(self):
        rows, hint = retention.load_csv(str(SAMPLES / "retention_short_seconds.csv"))
        report = retention.analyze(rows, axis_hint=hint)
        self.assertEqual(report["axis"], "seconds")
        self.assertEqual(report["hook_window_seconds"], 3)
        self.assertEqual(report["hook_leak"], 30)
        self.assertTrue(report["cliffs"])

    def test_transcript_quote(self):
        rows, hint = retention.load_csv(str(SAMPLES / "retention_short_seconds.csv"))
        cues = chapters.load(str(SAMPLES / "retention_quote.srt"))
        report = retention.analyze(rows, axis_hint=hint, cues=cues)
        blob = " ".join(report["said"].values())
        self.assertIn("這裡開始自介所以人走了", blob)

    def test_short_percent_is_not_the_long_window(self):
        rows, hint = retention.load_csv(str(SAMPLES / "retention_short_percent.csv"))
        report = retention.analyze(rows, duration=45, axis_hint=hint)
        self.assertEqual(report["axis"], "percent")
        self.assertEqual(report["hook_window_seconds"], 3)
        self.assertEqual(report["hook_leak"], 10)

    def test_long_percent_uses_thirty_seconds(self):
        rows, hint = retention.load_csv(str(SAMPLES / "retention_long_percent.csv"))
        report = retention.analyze(rows, duration=600, axis_hint=hint)
        self.assertEqual(report["hook_window_mode"], "long")
        self.assertEqual(report["hook_window_seconds"], 30)
        self.assertEqual(report["hook_leak"], 4)

    def test_percent_without_duration_is_honest(self):
        rows, hint = retention.load_csv(str(SAMPLES / "retention_long_percent.csv"))
        report = retention.analyze(rows, axis_hint=hint)
        self.assertEqual(report["hook_window_mode"], "percent-unknown")
        self.assertIsNone(report["hook_window_seconds"])

    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            retention.analyze([(0, 100), (1, 90)])


class SwipeTests(unittest.TestCase):
    def test_median_multiple_and_thin_channel(self):
        rows = json.loads((SAMPLES / "collected.json").read_text(encoding="utf-8"))
        report = swipe.rank(rows, minimum=2.0)
        self.assertEqual(len(report["outliers"]), 1)
        outlier = report["outliers"][0]
        self.assertEqual(outlier["multiple"], 4.55)
        self.assertEqual(outlier["median"], 1100)
        self.assertEqual(outlier["formula"], "統計數字")
        self.assertEqual(report["skipped_thin_channels"], [{"channel": "示範頻道乙", "count": 2}])


if __name__ == "__main__":
    unittest.main()
