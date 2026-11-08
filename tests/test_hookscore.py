import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    path = ROOT / rel
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


hookscore = load("hookscore", "skills/yt-script/hookscore.py")


class HookScoreTests(unittest.TestCase):
    def test_each_formula_example_classifies_as_itself(self):
        hooks = json.loads((ROOT / "skills/yt-script/hooks.json").read_text(encoding="utf-8"))
        for formula in hooks["hooks"]:
            name, hits = hookscore.classify(formula["example"])
            self.assertEqual(name, formula["name"], formula["example"])
            self.assertGreaterEqual(hits, 1)

    def test_english_hooks_still_classify(self):
        self.assertEqual(hookscore.classify("97% of people quit before video 30.")[0], "統計數字")
        self.assertEqual(hookscore.classify("Why do viewers leave so early?")[0], "觀眾的問題")
        self.assertEqual(
            hookscore.classify("If you have under a thousand subscribers, watch this.")[0],
            "點名觀眾",
        )

    def test_unclassified_plain_line(self):
        self.assertEqual(hookscore.classify("今天天氣不錯，出去走一下。")[0], "未對上公式")

    def test_short_hook_beats_vague_long_hook(self):
        good = hookscore.score("為什麼你會在第三秒滑走？")
        bad = hookscore.score(
            "今天要來分享一個超猛又必看的秘密，真的很重要，大家一定要看到最後因為這會讓你的人生變得完全不一樣"
        )
        self.assertGreaterEqual(good["verdict"], 55)
        self.assertLess(bad["verdict"], 45)
        self.assertEqual(good["properties"]["BREVITY"], 100)
        self.assertLess(bad["properties"]["BREVITY"], 40)
        self.assertLess(bad["properties"]["SPECIFICITY"], good["properties"]["SPECIFICITY"])
        self.assertLessEqual(good["spoken_seconds"], 3)

    def test_address_and_stakes_and_curiosity(self):
        plain = hookscore.score("封面字要短")
        named = hookscore.score("你的封面字要短")
        self.assertGreater(named["properties"]["ADDRESS"], plain["properties"]["ADDRESS"] + 20)
        stakes = hookscore.score("你會滑走")
        self.assertGreater(stakes["properties"]["STAKES"], plain["properties"]["STAKES"])
        asked = hookscore.score("為什麼？")
        closed = hookscore.score("為什麼？因為太長")
        self.assertGreater(asked["properties"]["CURIOSITY"], plain["properties"]["CURIOSITY"])
        self.assertGreater(asked["properties"]["CURIOSITY"], closed["properties"]["CURIOSITY"])

    def test_brevity_window(self):
        self.assertEqual(hookscore.brevity("你在第三秒會滑走"), 100)
        self.assertLess(hookscore.brevity("觀" * 40), 40)

    def test_empty_hook_does_not_crash(self):
        row = hookscore.score("   ")
        self.assertEqual(row["verdict"], 0)
        self.assertEqual(row["formula"], "未對上公式")


if __name__ == "__main__":
    unittest.main()
