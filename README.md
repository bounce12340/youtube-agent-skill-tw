# 台灣繁中短影音技能包

給拍 YouTube Shorts、IG Reels、TikTok，以及 Threads 配套文字的人。預設 3 分鐘以內，前 1 到 3 秒是開頭。技能負責寫，上傳始終由你自己按。

**這是改編，不是官方專案。** 上游是 Jake Schincariol 的 [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill)，授權 MIT。本倉庫釘在 commit [`a2feb2104981a375ffd4f87ee04f4f5344ac43c6`](https://github.com/Jakeschincariol/youtube-agent-skill/commit/a2feb2104981a375ffd4f87ee04f4f5344ac43c6)。上游作者不維護這份改編。機器可讀的同一份說明在 [`upstream.json`](upstream.json)。

十一個技能沿用上游的指令名，內容改寫成台灣繁中，工具改成能處理中文顯示寬度、口頭禪和雙語字幕。預設市場是台灣。香港、澳門、新加坡、中國大陸各有一份可分開改的設定，澳門不是香港的別名。程式只用 Python 標準函式庫，只讀本機檔案，沒有金鑰，也不會自己去網路上安裝或更新。

## 怎麼用

把需要的資料夾複製到你的技能目錄，或在對話裡貼上單份 `SKILL.md`。不要把倉庫網址貼進對話框當成安裝指令。這裡沒有從網址自我更新的安裝流程。

```bash
git clone <這個倉庫>
cp -r skills/yt-* <你的技能目錄>/
```

沒有技能目錄時，把單份 `SKILL.md` 放在對話開頭也能當工作模式。這樣會少掉六支 Python 工具。`/yt-script`、`/yt-package`、`/yt-edit`、`/yt-retention` 的重點就在那些工具。

先花十分鐘填 [`templates/voice.md`](templates/voice.md)。每一項技能都會讀它。短影音的句子你得親口講出來，語氣不對比沒有稿更糟。

## 十一個技能

| 指令 | 做什麼 |
| --- | --- |
| `/yt-script` | 一個點子寫成 3 分鐘內的腳本。五句開頭對上 [21 種公式](skills/yt-script/hooks.json)，評分後留下兩句。 |
| `/yt-package` | 標題和封面文字當一組檢查：顯示寬度、手機截斷、重複、空泛詞。 |
| `/yt-edit` | 字幕轉成剪輯清單：空檔、中文和英文口頭禪、重拍。支援雙語。 |
| `/yt-comment` | 留言分成問題、更正、稱讚、釣人，再用你的語氣起草回覆。 |
| `/yt-plan` | 依你真正有的時數排一週：一支主短影音、一支低成本、切片和 Threads。 |
| `/yt-viral` | 讀你已經整理好的本機清單，依相對自己帳號中位數的倍數排序。不預測熱門。 |
| `/yt-retention` | 讀觀看停留 CSV。短影音看前 3 秒，長片看前 30 秒。 |
| `/yt-shorts` | 寫能獨立存活的短影音，或從長片切出 Shorts、Reels、TikTok，並附 Threads 第一行。 |
| `/yt-seo` | 描述前兩行、少量用於消歧義的標籤、三句台灣觀眾會打的搜尋。 |
| `/yt-chapters` | 長片章節草稿，並檢查 YouTube 的三條規則。短影音可略過。 |
| `/yt-audit` | 看標題、封面、前三秒、節奏和停留，最後只留一個修正。 |

## 六個工具

乾淨的 Python 3.9 以上就能跑，沒有第三方套件。

```bash
python3 skills/yt-script/hookscore.py --hook "為什麼你會在第三秒滑走？"
python3 skills/yt-package/title.py --title "30 秒講完字幕" --cover "別自介"
python3 skills/yt-edit/deadair.py samples/transcript_edit.srt
python3 skills/yt-chapters/chapters.py samples/transcript_chapters.srt
python3 skills/yt-retention/retention.py samples/retention_short_seconds.csv
python3 skills/yt-viral/swipe.py samples/collected.json --min 2.0
python3 skills/yt-package/title.py --market mo --title "30 秒講完澳門通" --cover "別自介"
```

`--market` 可接 `tw`、`hk`、`mo`、`sg`、`cn`。省略時是 `tw`。六支工具都讀這個參數。不認識的代碼會以狀態碼 2 結束，不改你的句子。

## 五個市場

預設是台灣。另外四個是獨立設定檔，放在 `skills/_lib/markets/`。工具只標示用詞、口語詞、字形和引號，不改寫原句，也不做機械的繁簡轉換。看到差異時，檔案裡有各地的寫法可對，請自己決定要不要改。

| 代碼 | 標籤 | 文字 | 這份設定裡不一樣的地方 |
| --- | --- | --- | --- |
| `tw` | zh-TW | 繁體 | 預設。角引號。平台預設是 YouTube Shorts、Instagram Reels、TikTok、Threads。 |
| `hk` | zh-HK | 繁體，另有一份可刪的粵語口語詞 | 角引號。英文是基本法上的正式語文，不是貼文要求。平台預設是 YouTube、Instagram、Facebook、Threads。 |
| `mo` | zh-MO | 繁體，另有一份可刪的粵語口語詞 | 獨立檔案，不是 `hk` 的別名。角引號。葡文是基本法上的正式語文，不是貼文要求。平台預設和標題寬度都跟香港那份分開。 |
| `sg` | zh-SG | 簡體是這份設定的可編輯預設，可改回繁體 | 半形引號。可選的 lah、lor、leh、meh、hor 只用來檢查整格是不是只剩語氣詞。Singlish 不是憲法上的官方語言。平台預設是 YouTube、Instagram、TikTok、Facebook。 |
| `cn` | zh-CN | 簡體 | 彎引號。平台預設是抖音、嗶哩嗶哩、小紅書、微信視頻號。抖音和 TikTok 是不同產品。要加上 YouTube 或其他出口，直接改 JSON。 |

平台順序全部是可編輯預設。它不是使用率，也不是哪一個市場比較有效。創作者可以自行增刪。

下面這些連結只支持語文或 YouTube 標題長度。它們沒有說哪個平台比較多人用。

- 語言標籤 zh-TW、zh-HK、zh-MO、zh-SG、zh-CN：[IANA Language Subtag Registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry)
- 香港基本法第九條（中文與英文同為正式語文）：[基本法第一章](https://www.basiclaw.gov.hk/tc/basiclaw/chapter1.html)
- 澳門基本法第九條（中文與葡文同為正式語文）：[立法會文本](https://www.al.gov.mo/zh-hant/basic-law.html)、[公報文本](https://bo.dsaj.gov.mo/bo/i/1999/leibasicacn/)
- 新加坡憲法第 153A 條（馬來語、華語、淡米爾語、英語）：[SSO](https://sso.agc.gov.sg/Act/CONS1963?ProvIds=pr153A-)
- 《國家通用語言文字法》2001 年公報文本第二條（普通話和規範漢字）：[國務院公報](https://www.gov.cn/gongbao/content/2001/content_61066.htm)。後來若有修正，以最新公布文本為準。這裡不是合規解讀。
- YouTube 標題 100 個字元：[YouTube 說明](https://support.google.com/youtube/answer/57404)。這個數字只套在 YouTube 標題。這份設定沒有寫抖音、嗶哩嗶哩、小紅書或微信視頻號的字數上限。

`samples/markets/` 有五個市場的開頭例句，以及香港、澳門、新加坡、中國大陸的口頭禪字幕。`samples/markets/ambiguous.txt` 把「八達通」「軟體」「软件」放在一起，用來確認工具只標示、不改字。

`samples/` 裡有字幕、停留 CSV 和清單可以試。測試：

```bash
python3 -m unittest discover -s tests -v
```

## 限制

這些工具是檢查清單和啟發式，不是預測器。

**不能預測一支片會不會被大量觀看、轉發或完播。** `hookscore.py` 的五項權重沿用上游的形狀（平均六成、最弱項四成），窗口改成前 1 到 3 秒。上游曾用 74 段英文短片自動字幕做過校準，而且作者自己寫了：分得開故意寫壞的開頭和真的開頭，幾乎分不開同一位創作者的熱門和冷門。這份繁中改編沒有用台灣影片重做那次校準。低分值得重寫。高分不是承諾。

**口播秒數是粗估，而且五個市場用同一個速率。** 中文用 4.5 字／秒，英文用 2.5 個單字／秒。這個數字沒有按市場分開，也沒有說哪一種口語比較快。它只用來檢查開頭有沒有超過 3 秒。

**市場設定不是成效模型。** 用詞表、口頭禪、引號、標題寬度和平台順序都是可編輯預設。工具不預測某個市場比較容易被觀看。它也不把繁體和簡體逐字互轉。各地用詞若不只差在字形，只標示，不改寫原句。

**沒有合規或法律保證。** 基本法、憲法和語言文字法的連結只說明官方語文或公布文本寫了什麼。發布前請自己查看該平台目前的規則。

**100 字元只套在 YouTube 標題。** 其他平台的標題長度沒有寫進這份設定。Singlish 的語氣詞是可選檢查，不是官方語言，也不是寫作要求。

**公式只看字面。** `/yt-viral` 說某個標題像「統計數字」，判斷的是標題上的詞，不是觀看從哪裡來。

**顯示寬度是近似。** 繁中和簡中都算 2 格，半形英文算 1 格，東亞寬度表裡的歧義字算 2 格。台灣預設是桌面寬度 60、手機寬度 32、封面寬度 16。其他市場的寬度寫在各自的 JSON，也是可編輯預設，不是平台公布的截斷位置。YouTube 標題 100 字元的硬上限是字元數，不是顯示寬度，而且只在標題要放上 YouTube 時使用。

**口頭禪清單不是全集。** 只標整格都是「嗯、那個、就是、然後」或 um、you know 這類的字幕。句子裡夾一個「就是」故意不剪。新的語助詞會漏。單獨一格「好」若其實是回答，需要你在剪的時候略過。

**章節標題是草稿。** 中文邊界用常用字過濾後的二字組，不是斷詞器，也不是摘要模型。貼上前要改成你會講的話。短於 30 秒的片排不出三條合格章節。

**停留 CSV 描述已經發生的事。** 開頭流失取窗口內的最低點。百分比橫軸又沒給時長時，無法對準第 3 秒，只會暫用前 5%。

**`swipe.py` 不收集清單。** 它只讀本機 JSON。不上網、不登入、不讀憑證。一個帳號少於四支會被跳過，因為那不算中位數。

**不發佈，不發明數字。** 每一項技能的最後一行都是：「要發出，還是再改？」沒有的數字就不要寫成有。

**標籤不是策略。** 搜尋文案只用來消歧義，不用來塞詞。

## 授權

MIT。原著作權聲明保留在 [`LICENSE`](LICENSE)：Copyright (c) 2026 Jake Schincariol。改編部分同樣以 MIT 釋出。使用、修改、散佈時請保留該聲明，並註明這是改編而非官方專案。
