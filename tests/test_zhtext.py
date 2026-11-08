import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "_lib"))

import zhtext  # noqa: E402


class ZhTextTests(unittest.TestCase):
    def test_display_width_cjk_and_latin(self):
        self.assertEqual(zhtext.char_width("你"), 2)
        self.assertEqual(zhtext.char_width("A"), 1)
        self.assertEqual(zhtext.display_width("你A"), 3)
        self.assertEqual(zhtext.display_width("「你」"), 6)
        self.assertEqual(zhtext.char_width("，"), 2)
        self.assertEqual(zhtext.char_width("°"), 2)

    def test_truncate_display_rewinds_partial_latin_word(self):
        self.assertEqual(zhtext.truncate_display("hello world", 8), "hello")
        self.assertEqual(zhtext.truncate_display("你好世界", 4), "你好")
        self.assertEqual(zhtext.display_width(zhtext.truncate_display("字" * 20, 32)), 32)

    def test_spoken_seconds(self):
        # 你在第三秒會滑走 = 8 個中文字，4.5 字／秒。
        self.assertAlmostEqual(zhtext.spoken_seconds("你在第三秒會滑走"), 8 / 4.5, places=2)
        self.assertAlmostEqual(zhtext.spoken_seconds("one two three"), 1.2, places=2)

    def test_filler_lines(self):
        for line in ("嗯", "那個", "就是", "然後", "嗯，那個", "um", "you know", "好"):
            self.assertTrue(zhtext.is_filler_line(line), line)
        for line in ("就是這個設定", "好的，我們開始", "likewise", "something else", ""):
            self.assertFalse(zhtext.is_filler_line(line), line)

    def test_bilingual_cue(self):
        self.assertTrue(zhtext.is_filler_cue("嗯\num"))
        self.assertFalse(zhtext.is_filler_cue("The hold drops here.\n嗯"))
        self.assertFalse(zhtext.is_filler_cue("嗯\nThe hold drops here."))
        self.assertEqual(zhtext.script_mix("前三秒\nThe hold"), "bi")
        self.assertEqual(zhtext.script_mix("前三秒決定"), "zh")

    def test_opening_key_repeat(self):
        first = zhtext.opening_keys("前三秒要先講完播")
        second = zhtext.opening_keys("前三秒要先講完播，不要自介")
        self.assertTrue(first & second)

    def test_vague_does_not_match_inside_english_words(self):
        self.assertEqual(zhtext.vague_hits("The secretary problem explained"), [])
        self.assertIn("best", [item.lower() for item in zhtext.vague_hits("The best lens")])
        self.assertIn("必看", zhtext.vague_hits("這支必看，真的超猛"))
        self.assertNotIn("完播", zhtext.vague_hits("30 秒講完播"))

    def test_filler_word_boundary(self):
        self.assertEqual(zhtext.filler_hits("adjust the framing"), [])
        self.assertTrue(zhtext.filler_hits("就是這個"))

    def test_caption_tags(self):
        self.assertEqual(zhtext.clean_caption("<c>前三秒</c>"), "前三秒")


if __name__ == "__main__":
    unittest.main()
