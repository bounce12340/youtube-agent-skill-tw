import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


title = load("titlelint", "skills/yt-package/title.py")


def codes(row):
    return {item[0] for item in row["issues"]}


class TitleTests(unittest.TestCase):
    def test_clean_pair(self):
        row = title.check("30 秒講完字幕", "別自介")
        self.assertEqual(codes(row), set())
        self.assertLessEqual(row["display_width"], 32)

    def test_vague_and_mobile_and_hard_limit(self):
        vague = title.check("這支必看，真的超猛")
        self.assertIn("vague", codes(vague))
        self.assertIn("no-number", codes(vague))
        mobile = title.check("字" * 20)
        self.assertIn("mobile", codes(mobile))
        self.assertNotIn("length", codes(mobile))
        desktop = title.check("字" * 40)
        self.assertIn("length", codes(desktop))
        self.assertIn("mobile", codes(desktop))
        hard = title.check("字" * 101)
        self.assertIn("length", codes(hard))
        self.assertIn("101", hard["issues"][0][1])

    def test_cover_duplicate_and_length(self):
        dup = title.check("前三秒先講完播", "前三秒")
        self.assertIn("duplicate", codes(dup))
        clean = title.check("前三秒先講完播", "別自介")
        self.assertNotIn("duplicate", codes(clean))
        long_cover = title.check("前三秒先講完播", "別自介但是這行封面字真的太長了啦")
        self.assertIn("cover-length", codes(long_cover))

    def test_english_secret_boundary_and_shouting(self):
        secretary = title.check("The secretary problem explained")
        self.assertNotIn("vague", codes(secretary))
        best = title.check("The best lens for a desk")
        self.assertIn("vague", codes(best))
        loud = title.check("THIS IS VERY LOUD now")
        self.assertIn("shouting", codes(loud))

    def test_mobile_prefix_fits_width(self):
        raw = "字" * 20
        row = title.check(raw)
        message = next(item[1] for item in row["issues"] if item[0] == "mobile")
        shown = message.split("「", 1)[1].split("」", 1)[0]
        self.assertLessEqual(title.display_width(shown), 32)
        self.assertTrue(raw.startswith(shown))


if __name__ == "__main__":
    unittest.main()
