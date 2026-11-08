---
name: vp-cards
description: >-
  檢查疊字卡是否落在字幕的說話時間內，以及同一錨點是否同時兩張。不輸出 HTML。
---

# vp-cards

本檔是這份技能包裡另寫的檢查，不是 Jake Schincariol 的官方專案，也不是從 video-production-skills 複製的。該倉庫沒有授權條款。

```bash
python3 cards.py cards.json --transcript captions.srt --market mo --json
```

每張卡要有 `id`、`start`、`end`、`text`。`anchor` 省略時當 bottom。沒有和任何字幕重疊的卡會標未對上時間。同一錨點時間重疊會標出來。

工具只讀本機 JSON 和字幕。不畫卡片，不渲染。

## 市場

預設 `--market tw`。也可以用 `hk`、`mo`、`sg`、`cn`。文字寬度用該市場的可編輯預設。澳門不是香港的別名。

## 最後一關

這裡不發佈。每次輸出的最後一行都是：「要發出，還是再改？」
