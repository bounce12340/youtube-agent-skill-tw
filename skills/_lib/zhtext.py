# Adapted from Jake Schincariol's youtube-agent-skill (MIT).
# Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
# Pinned commit: a2feb2104981a375ffd4f87ee04f4f5344ac43c6
# This file is part of an adaptation, not the official project.
"""繁中短影音用的純標準函式庫文字工具。

顯示寬度、口播秒數、模糊詞、口頭禪、雙語字幕的開頭比對都放在這裡，
讓評分、標題與剪輯決策共用同一套規則。沒有網路、沒有第三方套件。
"""
from __future__ import annotations

import re
import unicodedata

# 台灣手機介面把寬字、全形字，以及東亞寬度表裡的歧義字，都當成兩格。
_WIDE = {"W", "F", "A"}

VAGUE_ZH = (
    "改變遊戲",
    "不看後悔",
    "建議收藏",
    "真的假的",
    "重點來了",
    "懂的都懂",
    "直接封神",
    "分享一下",
    "絕絕子",
    "閉眼入",
    "天花板",
    "有夠狂",
    "超猛",
    "超扯",
    "超強",
    "炸裂",
    "爆紅",
    "神作",
    "必看",
    "必收",
    "必追",
    "絕了",
    "很重要",
    "乾貨",
    "無腦",
    "厲害",
    "好棒",
    "太強",
    "無敵",
    "頂級",
    "終極",
    "秘密",
    "史詩",
    "完美",
    "驚艷",
    "震撼",
    "碼起來",
    "先馬",
    "封神",
    "最好",
    "yyds",
)

VAGUE_EN = (
    "mind-blowing",
    "mindblowing",
    "game-changer",
    "game changer",
    "unbelievable",
    "revolutionary",
    "incredible",
    "everything",
    "amazing",
    "insane",
    "massive",
    "ultimate",
    "powerful",
    "complete",
    "perfect",
    "secret",
    "crazy",
    "epic",
    "huge",
    "best",
)

# 整句都是這些詞才算口頭禪。長的放前面，避免「好」先吃掉「好的」。
FILLER_PHRASES = (
    "let me see",
    "you know",
    "i mean",
    "hold on",
    "basically",
    "actually",
    "anyway",
    "然後呢",
    "基本上",
    "你知道",
    "我是說",
    "等一下",
    "我想想",
    "怎麼說",
    "就是說",
    "okay",
    "yeah",
    "right",
    "like",
    "hmm",
    "對啊",
    "對呀",
    "對哦",
    "好的",
    "好喔",
    "其實",
    "反正",
    "那個",
    "就是",
    "然後",
    "歡迎收看",
    "大家好",
    "um",
    "uh",
    "er",
    "ah",
    "so",
    "ok",
    "嗯",
    "啊",
    "呃",
    "額",
    "喔",
    "哦",
    "哎",
    "欸",
    "蛤",
    "哈",
    "嘿",
    "啦",
    "嘛",
    "吧",
    "呢",
    "對",
    "好",
)

HOOK_FILLERS = (
    "歡迎收看",
    "大家好",
    "基本上",
    "其實",
    "那個",
    "就是",
    "然後",
    "各位",
    "哈囉",
    "今天",
    "訂閱",
    "basically",
    "actually",
    "literally",
    "welcome",
    "subscribe",
    "really",
    "just",
    "very",
)

STAKE_ZH = (
    "沒人看",
    "留不住",
    "來不及",
    "不要再",
    "觀看停",
    "白費",
    "白做",
    "浪費",
    "搞砸",
    "失敗",
    "後悔",
    "別再",
    "先別",
    "滑走",
    "掉粉",
    "風險",
    "停更",
)

CURIOSITY_ZH = (
    "為什麼",
    "為何",
    "怎麼",
    "如何",
    "居然",
    "原來",
    "除非",
    "到底",
    "但是",
    "可是",
)

CLOSED_ZH = ("因為", "所以", "意思是", "也就是")

FIGURE = re.compile(
    r"\d[\d,.]*\s?[%％萬千百秒分天週月年人支倍成]?"
    r"|百分之\s?[零一二三四五六七八九十兩\d]+"
    r"|[零一二三四五六七八兩九十百]+\s?[萬千秒分天週月年人支倍成]"
)

ADDRESS = re.compile(
    r"你們|妳們|你的|妳的|你|妳|(?<![A-Za-z])(you|your|you're|youre|yourself)(?![A-Za-z])",
    re.IGNORECASE,
)

STAKE_EN = re.compile(
    r"\b(lose|lost|wasting|waste|quit|fail|broke|cost|risk|stop|never)\b",
    re.IGNORECASE,
)

CURIOSITY_EN = re.compile(
    r"\b(why|how|what|which|until|nobody|almost|except|reason)\b",
    re.IGNORECASE,
)

CLOSED_EN = re.compile(r"\b(because|so that|which means)\b", re.IGNORECASE)

EN_STOP = {
    "the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are",
    "was", "were", "be", "been", "with", "this", "that", "it", "as", "at", "by",
    "from", "you", "your", "i", "my", "we", "our", "they", "them", "he", "she",
    "but", "so", "if", "then", "than", "there", "here", "what", "which", "who",
    "how", "when", "where", "why", "not", "no", "yes", "do", "does", "did",
    "just", "really", "very", "like", "about", "into", "over", "out", "up",
    "down", "can", "could", "will", "would", "should", "have", "has", "had",
    "get", "got", "make", "made", "go", "going", "went", "one", "two",
}

STOP_CHARS = set("的了是在我你他她它就都也很把被這那個和與或但而又及嗎呢吧啊喔到從對為以能會要有沒不又再還讓給跟去來說看做用")


def char_width(ch: str) -> int:
    if not ch or unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in _WIDE:
        return 2
    return 1


def display_width(text: str) -> int:
    return sum(char_width(ch) for ch in text)


def truncate_display(text: str, max_width: int) -> str:
    """截到指定顯示寬度。拉丁單字被切到一半時，退回上一個空格。"""
    if max_width <= 0:
        return ""
    if display_width(text) <= max_width:
        return text
    out: list[str] = []
    width = 0
    for ch in text:
        cw = char_width(ch)
        if width + cw > max_width:
            break
        out.append(ch)
        width += cw
    cut = "".join(out)
    if not cut:
        return ""
    next_index = len(cut)
    if next_index < len(text) and text[next_index] not in " \u3000" and cut[-1] not in " \u3000":
        # 只在切點落在半形英文單字中間時退回空格。中文一字一義，不退。
        if cut[-1].isascii() and cut[-1].isalnum():
            space = max(cut.rfind(" "), cut.rfind("\u3000"))
            if space > 0:
                cut = cut[:space]
    return cut.rstrip()


def cjk_chars(text: str) -> list[str]:
    chars = []
    for ch in text:
        code = ord(ch)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0x3040 <= code <= 0x30FF
            or 0xAC00 <= code <= 0xD7AF
        ):
            chars.append(ch)
    return chars


def latin_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)


def spoken_seconds(text: str) -> float:
    """口播秒數粗估：中文約 4.5 字／秒，英文約 2.5 個單字／秒。

    這是短影音清楚口播的經驗值，不是語音辨識，也不能用來保證完播。
    """
    return len(cjk_chars(text)) / 4.5 + len(latin_words(text)) / 2.5


def normalize_spaces(text: str) -> str:
    out: list[str] = []
    for ch in text.lower().replace("\u3000", " "):
        cat = unicodedata.category(ch)
        if ch.isspace() or cat.startswith(("P", "S")):
            out.append(" ")
        else:
            out.append(ch)
    return re.sub(r" +", " ", "".join(out)).strip()


def is_filler_line(line: str) -> bool:
    """整行只剩口頭禪才回傳 True。句子裡夾一個「就是」不算。"""
    s = normalize_spaces(line)
    if not s:
        return False
    phrases = sorted(FILLER_PHRASES, key=len, reverse=True)
    i = 0
    n = len(s)
    found = False
    while i < n:
        while i < n and s[i] == " ":
            i += 1
        if i >= n:
            break
        hit = None
        for phrase in phrases:
            if not s.startswith(phrase, i):
                continue
            end = i + len(phrase)
            if phrase.isascii() and end < n and s[end].isascii() and s[end].isalpha():
                continue
            hit = end
            break
        if hit is None:
            return False
        found = True
        i = hit
    return found


def content_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines or ([text.strip()] if text.strip() else [])


def is_filler_cue(text: str) -> bool:
    """雙語字幕：每一行都是口頭禪才整格刪。一行有內容就保留。"""
    lines = content_lines(text)
    if not lines:
        return False
    return all(is_filler_line(ln) for ln in lines)


def script_mix(text: str) -> str:
    has_cjk = bool(cjk_chars(text))
    has_en = bool(latin_words(text))
    if has_cjk and has_en:
        return "bi"
    if has_cjk:
        return "zh"
    if has_en:
        return "en"
    return "other"


def opening_key(line: str) -> tuple | None:
    if is_filler_line(line):
        return None
    cjk = cjk_chars(line)
    if len(cjk) >= 4:
        return ("cjk", "".join(cjk[:8]))
    words = [w.lower() for w in latin_words(line)]
    if len(words) >= 3:
        return ("en", tuple(words[:5]))
    return None


def opening_keys(text: str) -> set[tuple]:
    keys = set()
    for line in content_lines(text):
        key = opening_key(line)
        if key:
            keys.add(key)
    return keys


def find_zh_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    occupied = [False] * len(text)
    folded = text.lower()
    for phrase in sorted(phrases, key=len, reverse=True):
        needle = phrase.lower()
        start = 0
        while True:
            index = folded.find(needle, start)
            if index < 0:
                break
            end = index + len(needle)
            if not any(occupied[index:end]):
                found.append(phrase)
                for pos in range(index, end):
                    occupied[pos] = True
            start = end
    return found


def find_en_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    found = []
    for phrase in phrases:
        if re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE):
            found.append(phrase)
    return found


def vague_hits(text: str) -> list[str]:
    return find_zh_phrases(text, VAGUE_ZH) + find_en_phrases(text, VAGUE_EN)


def filler_hits(text: str) -> list[str]:
    zh = tuple(phrase for phrase in HOOK_FILLERS if not phrase.isascii())
    en = tuple(phrase for phrase in HOOK_FILLERS if phrase.isascii())
    return find_zh_phrases(text, zh) + find_en_phrases(text, en)


def figure_spans(text: str) -> list[str]:
    return [m.group(0) for m in FIGURE.finditer(text)]


def has_figure(text: str) -> bool:
    if re.search(r"\d", text):
        return True
    return bool(figure_spans(text))


def content_grams(text: str) -> set[str]:
    grams: set[str] = set()
    for word in re.findall(r"[a-z]{4,}", text.lower()):
        if word not in EN_STOP:
            grams.add(word)
    chars = [ch for ch in cjk_chars(text) if ch not in STOP_CHARS]
    for index in range(len(chars) - 1):
        grams.add(chars[index] + chars[index + 1])
    return grams


def clean_caption(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    for src, dst in (
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ):
        text = text.replace(src, dst)
    return text.strip()


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))
