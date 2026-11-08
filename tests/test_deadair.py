import importlib.util
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


deadair = load("deadair", "skills/yt-edit/deadair.py")


def kinds(report):
    return {cut["kind"] for cut in report["cuts"]}


class DeadAirTests(unittest.TestCase):
    def test_sample_srt_finds_filler_dead_and_repeat(self):
        report = deadair.analyze(str(SAMPLES / "transcript_edit.srt"))
        self.assertEqual(kinds(report), {"FILLER", "DEAD", "REPEAT"})
        fillers = [cut["why"] for cut in report["cuts"] if cut["kind"] == "FILLER"]
        self.assertTrue(any("嗯" in item for item in fillers))
        self.assertTrue(any("那個" in item for item in fillers))

    def test_floor_keeps_short_breath(self):
        cues = [
            (0.0, 1.0, "前三秒要先講完播"),
            (1.4, 3.0, "後面這句換成別的內容"),
        ]
        self.assertFalse(any(cut["kind"] == "DEAD" for cut in deadair.build_cuts(cues, 0.45)))
        cues[1] = (1.5, 3.0, "後面這句換成別的內容")
        self.assertTrue(any(cut["kind"] == "DEAD" for cut in deadair.build_cuts(cues, 0.45)))

    def test_bilingual_vtt_keeps_content_line(self):
        cues = deadair.load(str(SAMPLES / "transcript_bilingual.vtt"))
        self.assertEqual(len(cues), 3)
        blob = "\n".join(cue[2] for cue in cues)
        self.assertNotIn("should not become", blob)
        report = deadair.analyze(str(SAMPLES / "transcript_bilingual.vtt"))
        filler = [cut for cut in report["cuts"] if cut["kind"] == "FILLER"]
        self.assertEqual(len(filler), 1)
        self.assertIn("嗯", filler[0]["why"])
        self.assertIn("DEAD", kinds(report))
        first = cues[0][2]
        self.assertIn("前三秒", first)
        self.assertIn("first three seconds", first)

    def test_whisper_json(self):
        report = deadair.analyze(str(SAMPLES / "whisper_zh.json"))
        self.assertIn("FILLER", kinds(report))
        self.assertIn("DEAD", kinds(report))

    def test_repeat_skips_filler_between_takes(self):
        cues = [
            (0.0, 1.2, "前三秒要先講完播"),
            (1.2, 1.6, "嗯"),
            (1.6, 3.0, "前三秒要先講完播，不要自介"),
        ]
        repeats = [cut for cut in deadair.build_cuts(cues, 0.45) if cut["kind"] == "REPEAT"]
        self.assertEqual(len(repeats), 1)
        self.assertEqual(repeats[0]["start"], 0.0)


if __name__ == "__main__":
    unittest.main()
