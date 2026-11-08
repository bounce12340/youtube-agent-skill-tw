import ast
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SAMPLES = ROOT / "samples" / "markets"


def load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


zhtext = load("zhtext", "skills/_lib/zhtext.py")
markets = load("markets", "skills/_lib/markets.py")
title = load("titlelint", "skills/yt-package/title.py")
deadair = load("deadair", "skills/yt-edit/deadair.py")
hookscore = load("hookscore", "skills/yt-script/hookscore.py")


def codes(row):
    return {item[0] for item in row["issues"]}


def kinds(flags):
    return {item["kind"] for item in flags}


class MarketProfileTests(unittest.TestCase):
    def test_every_market_loads_and_only_taiwan_is_default(self):
        self.assertEqual(markets.IDS, ("tw", "hk", "mo", "sg", "cn"))
        defaults = []
        for code in markets.IDS:
            profile = markets.get_market(code)
            raw = json.loads((ROOT / "skills" / "_lib" / "markets" / f"{code}.json").read_text(encoding="utf-8"))
            for key in markets.REQUIRED:
                self.assertIn(key, profile, code)
            self.assertEqual(profile["id"], code)
            self.assertNotIn("alias_of", raw)
            self.assertEqual(profile["layout"]["youtube_title_chars"], 100)
            self.assertNotIn("spoken_rate", profile)
            if profile["default"]:
                defaults.append(code)
        self.assertEqual(defaults, ["tw"])
        self.assertEqual(markets.get_market(None)["id"], "tw")
        self.assertEqual(markets.get_market("")["id"], "tw")

    def test_macau_is_not_hong_kong(self):
        hk = markets.get_market("hk")
        mo = markets.get_market("mo")
        self.assertNotEqual(hk, mo)
        self.assertNotEqual(hk["fillers"], mo["fillers"])
        self.assertNotEqual(hk["example_hook"], mo["example_hook"])
        self.assertNotEqual(hk["layout"]["mobile_width"], mo["layout"]["mobile_width"])
        self.assertNotEqual(hk["colloquial"], mo["colloquial"])
        self.assertEqual(hk["companion_language"], "en")
        self.assertEqual(mo["companion_language"], "pt")
        self.assertIn("英", hk["official_language_note"])
        self.assertIn("葡", mo["official_language_note"])
        self.assertNotEqual([item["id"] for item in hk["platforms"]], [item["id"] for item in mo["platforms"]])
        self.assertIn("吓", hk["fillers"])
        self.assertNotIn("吓", mo["fillers"])
        self.assertIn("喂呀", mo["fillers"])
        self.assertNotIn("喂呀", hk["fillers"])
        self.assertIn("唔該", hk["colloquial"])
        self.assertNotIn("唔該", mo["colloquial"])
        self.assertIn("呢邊", mo["colloquial"])
        self.assertNotIn("呢邊", hk["colloquial"])
        self.assertNotIn("天花板", mo["vague"])
        self.assertIn("正到爆", mo["vague"])

    def test_taiwan_lists_match_the_existing_checker(self):
        tw = markets.get_market("tw")
        self.assertEqual(tuple(tw["fillers"]), zhtext.FILLER_PHRASES)
        self.assertEqual(tuple(tw["vague"]), zhtext.VAGUE_ZH)
        self.assertEqual(tw["layout"]["desktop_width"], 60)
        self.assertEqual(tw["layout"]["mobile_width"], 32)
        self.assertEqual(tw["layout"]["cover_width"], 16)
        self.assertEqual(tw["script"], "hant")
        self.assertEqual(markets.get_market("hk")["script"], "hant")
        self.assertEqual(markets.get_market("mo")["script"], "hant")
        self.assertEqual(markets.get_market("sg")["script"], "hans")
        self.assertEqual(markets.get_market("cn")["script"], "hans")

    def test_loader_rejects_alias_and_unknown_market(self):
        source = (ROOT / "skills" / "_lib" / "markets.py").read_text(encoding="utf-8")
        self.assertNotIn("opencc", source.lower())
        self.assertNotIn("def convert", source)
        tree = ast.parse(source)
        names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        self.assertNotIn("convert", names)
        with self.assertRaises(markets.MarketError):
            markets.get_market("xx")
        code, kept = markets.pop_market(["--market", "mo", "file.srt"])
        self.assertEqual(code, "mo")
        self.assertEqual(kept, ["file.srt"])
        code, kept = markets.pop_market(["--title", "字幕", "--market=hk"])
        self.assertEqual((code, kept), ("hk", ["--title", "字幕"]))
        self.assertEqual(markets.pop_market([])[0], "tw")

    def test_flags_do_not_rewrite(self):
        original = "我用軟體"
        flags = markets.flag_terms(original, "cn")
        self.assertEqual(original, "我用軟體")
        wording = [item for item in flags if item["kind"] == "wording"]
        self.assertEqual(len(wording), 1)
        self.assertEqual(wording[0]["id"], "software")
        self.assertEqual(wording[0]["action"], "flag_only")
        self.assertNotIn("script", kinds(flags))
        simplified = "我用软件"
        flags = markets.flag_terms(simplified, "tw")
        self.assertEqual(simplified, "我用软件")
        self.assertEqual(flags[0]["id"], "software")
        self.assertNotIn("script", kinds(flags))

    def test_card_names_stay_in_their_markets(self):
        mo_flags = markets.flag_terms("八達通", "mo")
        self.assertEqual(mo_flags[0]["id"], "stored_value_card")
        self.assertIn("澳門通", mo_flags[0]["forms"]["mo"])
        self.assertEqual(markets.flag_terms("八達通", "hk"), [])
        hk_flags = markets.flag_terms("澳門通", "hk")
        self.assertEqual(hk_flags[0]["id"], "stored_value_card")
        self.assertIn("mo", hk_flags[0]["seen_in"])
        self.assertEqual(markets.flag_terms("澳門通", "mo"), [])
        self.assertEqual(markets.flag_terms("軟件", "hk"), [])
        self.assertEqual(markets.flag_terms("軟件", "mo"), [])
        blob = (SAMPLES / "ambiguous.txt").read_text(encoding="utf-8")
        self.assertIn("八達通", blob)
        self.assertIn("軟件", blob)
        flagged = markets.flag_terms(blob, "mo")
        self.assertTrue(any(item["term"] == "八達通" for item in flagged))
        self.assertFalse(any(item["term"] == "軟件" for item in flagged))
        self.assertEqual(blob, (SAMPLES / "ambiguous.txt").read_text(encoding="utf-8"))

    def test_each_sample_hook_is_not_flagged_in_its_own_market(self):
        for code in markets.IDS:
            profile = markets.get_market(code)
            sample = (SAMPLES / f"hooks_{code}.txt").read_text(encoding="utf-8").strip()
            self.assertEqual(sample, profile["example_hook"])
            flags = markets.flag_terms(sample, code)
            self.assertNotIn("wording", kinds(flags), flags)
            self.assertNotIn("script", kinds(flags), flags)
            self.assertNotIn("colloquial", kinds(flags), flags)
            row = hookscore.score(sample, code)
            self.assertEqual(row["hook"], sample)
            self.assertEqual(row["market"], code)
            self.assertEqual(row["locale"], profile["locale"])

    def test_colloquial_and_quotes_are_flags_only(self):
        self.assertEqual(markets.flag_terms("吓", "hk"), [])
        mo = markets.flag_terms("吓", "mo")
        self.assertEqual(mo[0]["kind"], "colloquial")
        self.assertEqual(markets.flag_terms("喂呀", "mo"), [])
        hk = markets.flag_terms("喂呀", "hk")
        self.assertEqual(hk[0]["kind"], "colloquial")
        corner = "標題用「字幕」"
        cn_flags = markets.flag_terms(corner, "cn")
        self.assertEqual(corner, "標題用「字幕」")
        self.assertIn("quote", kinds(cn_flags))
        curly = "標題用“字幕”"
        tw_flags = markets.flag_terms(curly, "tw")
        self.assertIn("quote", kinds(tw_flags))
        self.assertNotIn("quote", kinds(markets.flag_terms('say "ok"', "tw")))

    def test_filler_words_follow_the_market(self):
        hk = tuple(markets.get_market("hk")["fillers"])
        mo = tuple(markets.get_market("mo")["fillers"])
        sg = tuple(markets.get_market("sg")["fillers"])
        sg_suffix = tuple(markets.get_market("sg")["suffix_particles"])
        cn = tuple(markets.get_market("cn")["fillers"])
        self.assertTrue(zhtext.is_filler_line("吓", hk))
        self.assertFalse(zhtext.is_filler_line("吓", mo))
        self.assertFalse(zhtext.is_filler_line("吓"))
        self.assertTrue(zhtext.is_filler_line("喂呀", mo))
        self.assertFalse(zhtext.is_filler_line("喂呀", hk))
        self.assertTrue(zhtext.is_filler_line("ok lah", sg, sg_suffix))
        self.assertTrue(zhtext.is_filler_line("okaylah", sg, sg_suffix))
        self.assertFalse(zhtext.is_filler_line("ok lah"))
        self.assertTrue(zhtext.is_filler_line("那个", cn))
        self.assertFalse(zhtext.is_filler_line("那个"))
        self.assertTrue(zhtext.is_filler_line("那個"))

    def test_deadair_keeps_flags_out_of_cuts(self):
        hk_path = str(SAMPLES / "hk_filler.srt")
        on_hk = deadair.analyze(hk_path, market="hk")
        on_mo = deadair.analyze(hk_path, market="mo")
        self.assertIn("FILLER", {cut["kind"] for cut in on_hk["cuts"]})
        self.assertNotIn("FILLER", {cut["kind"] for cut in on_mo["cuts"]})
        self.assertTrue(all(cut["kind"] in {"FILLER", "DEAD", "REPEAT"} for cut in on_hk["cuts"]))
        self.assertEqual(on_mo["market"], "mo")
        mo_path = str(SAMPLES / "mo_filler.srt")
        self.assertIn("FILLER", {cut["kind"] for cut in deadair.analyze(mo_path, market="mo")["cuts"]})
        self.assertNotIn("FILLER", {cut["kind"] for cut in deadair.analyze(mo_path, market="hk")["cuts"]})
        sg_path = str(SAMPLES / "sg_filler.srt")
        self.assertIn("FILLER", {cut["kind"] for cut in deadair.analyze(sg_path, market="sg")["cuts"]})
        self.assertNotIn("FILLER", {cut["kind"] for cut in deadair.analyze(sg_path, market="tw")["cuts"]})
        cn_path = str(SAMPLES / "cn_filler.srt")
        self.assertIn("FILLER", {cut["kind"] for cut in deadair.analyze(cn_path, market="cn")["cuts"]})
        self.assertNotIn("FILLER", {cut["kind"] for cut in deadair.analyze(cn_path, market="tw")["cuts"]})

    def test_title_widths_are_per_market_defaults(self):
        wide = "字" * 17
        self.assertEqual(zhtext.display_width(wide), 34)
        self.assertIn("mobile", codes(title.check(wide, market="tw")))
        self.assertIn("mobile", codes(title.check(wide, market="mo")))
        self.assertNotIn("mobile", codes(title.check(wide, market="sg")))
        cover = "字" * 8
        self.assertEqual(zhtext.display_width(cover), 16)
        base = "30 秒講完字幕"
        self.assertIn("cover-length", codes(title.check(base, cover, "hk")))
        self.assertIn("cover-length", codes(title.check(base, cover, "cn")))
        self.assertNotIn("cover-length", codes(title.check(base, cover, "tw")))
        self.assertNotIn("cover-length", codes(title.check(base, cover, "sg")))
        self.assertNotIn("cover-length", codes(title.check(base, cover, "mo")))
        clean = title.check("30 秒講完字幕", "別自介")
        self.assertEqual(codes(clean), set())
        self.assertEqual(clean["term_flags"], [])
        self.assertEqual(clean["market"], "tw")

    def test_cli_market_switch(self):
        for code, locale in (
            ("tw", "zh-TW"),
            ("hk", "zh-HK"),
            ("mo", "zh-MO"),
            ("sg", "zh-SG"),
            ("cn", "zh-CN"),
        ):
            result = subprocess.run(
                [PY, "skills/yt-package/title.py", "--market", code, "--title", "30 秒講完字幕", "--json"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            row = json.loads(result.stdout)[0]
            self.assertEqual(row["market"], code)
            self.assertEqual(row["locale"], locale)
            self.assertEqual(row["title"], "30 秒講完字幕")
        unknown = subprocess.run(
            [PY, "skills/yt-package/title.py", "--market", "xx", "--title", "30 秒講完字幕", "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(unknown.returncode, 2)

    def test_docs_name_macau_and_the_limits(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("澳門", readme)
        self.assertIn("zh-MO", readme)
        self.assertIn("可編輯預設", readme)
        self.assertIn("不改寫原句", readme)
        self.assertIn("發布前請自己查看該平台目前的規則", readme)
        skills = list((ROOT / "skills").glob("yt-*/SKILL.md"))
        self.assertEqual(len(skills), 11)
        for path in skills:
            self.assertIn("--market", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
