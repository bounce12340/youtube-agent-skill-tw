import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SAMPLES = ROOT / "samples" / "vp"
VIDEO_COMMIT = "f80248b5e2e41286a6ad5662601e0aa41e121201"


def load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


board = load("vp_board", "skills/vp-storyboard/board.py")
ledger = load("vp_ledger", "skills/vp-assets/ledger.py")
layout = load("vp_layout", "skills/vp-captions/layout.py")
mixcheck = load("vp_mix", "skills/vp-mix/mixcheck.py")
cards = load("vp_cards", "skills/vp-cards/cards.py")
exportcheck = load("vp_export", "skills/vp-export/exportcheck.py")
markets = load("markets", "skills/_lib/markets.py")
deadair = load("deadair", "skills/yt-edit/deadair.py")


def codes(report):
    return {item[0] for item in report["issues"]}


class ProductionCheckTests(unittest.TestCase):
    def test_storyboards_for_every_market_are_clean(self):
        for code in markets.IDS:
            path = SAMPLES / f"storyboard_{code}.json"
            original = path.read_text(encoding="utf-8")
            report = board.check(json.loads(original), code)
            self.assertEqual(codes(report), set(), report["issues"])
            self.assertEqual(report["market"], code)
            self.assertNotIn("wording", {item["kind"] for item in report["term_flags"]})
            self.assertNotIn("script", {item["kind"] for item in report["term_flags"]})
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_storyboard_overlap_and_cramped_speech(self):
        report = board.check({
            "duration": 3,
            "shots": [
                {"id": "a", "start": 0, "end": 2, "on_screen": "字" * 20, "spoken": "為什麼你會在第三秒滑走？"},
                {"id": "b", "start": 1, "end": 3, "on_screen": "下一個", "spoken": "短"},
            ],
        }, "tw")
        self.assertIn("overlap", codes(report))
        self.assertIn("wide-text", codes(report))
        self.assertIn("cramped", codes(report))
        wide = board.check({
            "shots": [{"id": "a", "start": 0, "end": 4, "on_screen": "字" * 17, "spoken": "短"}],
        }, "sg")
        self.assertNotIn("wide-text", codes(wide))

    def test_ledger_rejects_escape_and_blank_label(self):
        clean = ledger.check(json.loads((SAMPLES / "assets.json").read_text(encoding="utf-8")))
        self.assertEqual(codes(clean), set())
        report = ledger.check({
            "assets": [
                {"id": "x", "path": "../secret.mp4", "source": "", "license_label": ""},
                {"id": "x", "path": "/tmp/a.mp4", "source": "disk", "license_label": "own"},
            ]
        })
        self.assertIn("path", codes(report))
        self.assertIn("source", codes(report))
        self.assertIn("license-label", codes(report))
        self.assertIn("duplicate-id", codes(report))
        self.assertNotIn("heygen", json.dumps(report).lower())

    def test_caption_layout_across_markets(self):
        for code in markets.IDS:
            cues = deadair.load(str(SAMPLES / f"captions_{code}.srt"))
            report = layout.check(cues, code)
            self.assertEqual(codes(report), set(), report["issues"])
            self.assertEqual(report["locale"], markets.get_market(code)["locale"])
        fast = layout.check([(0.0, 0.4, "為什麼你會在第三秒滑走？")], "tw")
        self.assertIn("too-fast", codes(fast))
        wide = layout.check([(0.0, 4.0, "字" * 17)], "mo")
        self.assertIn("wide-line", codes(wide))
        roomy = layout.check([(0.0, 4.0, "字" * 17)], "sg")
        self.assertNotIn("wide-line", codes(roomy))
        stacked = layout.check([(0.0, 2.0, "一\n二\n三")], "tw")
        self.assertIn("lines", codes(stacked))

    def test_mix_plan_duck_fade_and_clip(self):
        clean = mixcheck.check(json.loads((SAMPLES / "mix.json").read_text(encoding="utf-8")))
        self.assertEqual(codes(clean), set(), clean["issues"])
        shallow = mixcheck.check({
            "clips": [
                {"id": "vo", "role": "voice", "start": 0, "end": 4, "gain_db": -3, "peak_dbfs": -3},
                {"id": "bed", "role": "music", "start": 0, "end": 4, "gain_db": -4, "fade_in": 0.2, "fade_out": 0.2, "peak_dbfs": -6},
            ]
        })
        self.assertIn("duck-shallow", codes(shallow))
        declared = mixcheck.check({
            "clips": [
                {"id": "vo", "role": "voice", "start": 0, "end": 4, "gain_db": -3, "peak_dbfs": -3},
                {"id": "bed", "role": "music", "start": 0, "end": 4, "gain_db": -4, "fade_in": 0.2, "fade_out": 0.2, "peak_dbfs": -6, "duck_db": 8},
            ]
        })
        self.assertNotIn("duck-shallow", codes(declared))
        messy = mixcheck.check({
            "clips": [
                {"id": "hit", "role": "sfx", "start": 0, "end": 1, "gain_db": 3, "fade_in": 0.8, "fade_out": 0.8, "peak_dbfs": 0.2},
            ]
        })
        self.assertIn("clip-risk", codes(messy))
        self.assertIn("fade-overrun", codes(messy))
        self.assertIn("near-clip", codes(messy))
        unknown = mixcheck.check({
            "clips": [
                {"id": "vo", "role": "voice", "start": 0, "end": 2, "gain_db": -3, "fade_in": 0, "fade_out": 0},
            ]
        })
        self.assertIn("peak-unknown", codes(unknown))

    def test_cards_must_overlap_transcript(self):
        for code in markets.IDS:
            cues = deadair.load(str(SAMPLES / f"captions_{code}.srt"))
            report = cards.check(json.loads((SAMPLES / f"cards_{code}.json").read_text(encoding="utf-8")), cues, code)
            self.assertEqual(codes(report), set(), report["issues"])
            self.assertFalse(any(item["kind"] == "script" for item in report["term_flags"]))
        cues = [(0.0, 2.0, "有一句話")]
        late = cards.check({"cards": [
            {"id": "a", "start": 3, "end": 4, "text": "晚了", "anchor": "bottom"},
            {"id": "b", "start": 0.2, "end": 1.0, "text": "同時", "anchor": "bottom"},
            {"id": "c", "start": 0.4, "end": 1.2, "text": "也在", "anchor": "bottom"},
        ]}, cues, "hk")
        self.assertIn("untimed", codes(late))
        self.assertIn("stack", codes(late))

    def test_export_preset_and_saved_probe_json(self):
        clean = exportcheck.check(
            json.loads((SAMPLES / "export.json").read_text(encoding="utf-8")),
            exportcheck.load_target("vertical", None),
        )
        self.assertEqual(codes(clean), set(), clean["issues"])
        small = exportcheck.check(
            {"container": "mp4", "duration": 10, "video": {"width": 720, "height": 1280, "fps": 24},
             "audio": {"sample_rate": 44100, "channels": 1, "peak_dbfs": -3}},
            exportcheck.load_target("vertical", None),
        )
        self.assertIn("frame", codes(small))
        self.assertIn("fps", codes(small))
        self.assertIn("sample-rate", codes(small))
        self.assertIn("channels", codes(small))
        probed = exportcheck.manifest_from_ffprobe({
            "format": {"duration": "12.5", "format_name": "mov,mp4,m4a"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920, "avg_frame_rate": "30/1", "codec_name": "h264"},
                {"codec_type": "audio", "sample_rate": "48000", "channels": 2, "codec_name": "aac"},
            ],
        })
        self.assertEqual(probed["video"]["fps"], 30)
        self.assertEqual(probed["container"], "mp4")
        report = exportcheck.check(probed, exportcheck.load_target("vertical", None))
        self.assertIn("peak-unknown", codes(report))
        self.assertNotIn("frame", codes(report))

    def test_report_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "report.json"
            target.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(exportcheck.write_json.__globals__["IoError"]):
                exportcheck.write_json(str(target), {"ok": True}, overwrite=False)
            self.assertEqual(target.read_text(encoding="utf-8"), "{}\n")
            exportcheck.write_json(str(target), {"ok": True}, overwrite=True)
            self.assertIn("ok", target.read_text(encoding="utf-8"))

    def test_cli_markets_and_unknown(self):
        for code in ("tw", "hk", "mo", "sg", "cn"):
            result = subprocess.run(
                [PY, "skills/vp-storyboard/board.py", f"samples/vp/storyboard_{code}.json", "--market", code, "--json"],
                cwd=ROOT, check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            row = json.loads(result.stdout)
            self.assertEqual(row["market"], code)
            self.assertEqual(row["issues"], [])
        unknown = subprocess.run(
            [PY, "skills/vp-export/exportcheck.py", "samples/vp/export.json", "--market", "xx", "--json"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        self.assertEqual(unknown.returncode, 2)
        mix = subprocess.run(
            [PY, "skills/vp-mix/mixcheck.py", "samples/vp/mix.json", "--json"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        self.assertEqual(mix.returncode, 0, mix.stderr)
        self.assertEqual(json.loads(mix.stdout)["issues"], [])

    def test_license_boundary_and_no_copied_services(self):
        pin = json.loads((ROOT / "upstream-video.json").read_text(encoding="utf-8"))
        self.assertEqual(pin["commit"], VIDEO_COMMIT)
        self.assertIsNone(pin["license"])
        self.assertFalse(pin["copied"])
        youtube = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))
        self.assertEqual(youtube["commit"], "a2feb2104981a375ffd4f87ee04f4f5344ac43c6")
        self.assertEqual(youtube["license"], "MIT")
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Jake Schincariol", license_text)
        self.assertIn(VIDEO_COMMIT, license_text)
        self.assertIn("no license", license_text.lower())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(VIDEO_COMMIT, readme)
        self.assertIn("沒有複製", readme)
        needles = ("heygen", "posthog", "telemetry", "hyperframes")
        for path in (ROOT / "skills").glob("vp-*/**/*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for needle in needles:
                self.assertNotIn(needle, text, path)
        lib = (ROOT / "skills" / "_lib" / "vpio.py").read_text(encoding="utf-8").lower()
        for needle in needles:
            self.assertNotIn(needle, lib)
        skills = list((ROOT / "skills").glob("vp-*/SKILL.md"))
        self.assertEqual(len(skills), 6)
        for path in skills:
            text = path.read_text(encoding="utf-8")
            self.assertIn("--market", text)
            self.assertIn("要發出，還是再改？", text)
            self.assertIn("沒有授權", text)


if __name__ == "__main__":
    unittest.main()
