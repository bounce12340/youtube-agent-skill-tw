---
name: vp-storyboard
description: >-
  檢查本機分鏡 JSON 的時間是否接得上、畫面字是否超過該市場的可編輯寬度。
  不評開頭公式，不預測觀看。
---

# vp-storyboard

本檔是這份技能包裡另寫的檢查，不是 Jake Schincariol 的官方專案，也不是從 video-production-skills 複製的。該倉庫沒有授權條款。

```bash
python3 board.py storyboard.json --market tw --json
```

每個鏡頭要有 `id`、`start`、`end`。`on_screen` 是畫面上的字，`spoken` 是口播。`duration` 可省略。

工具只標時間重疊、過長的空檔、口播粗估放不進鏡頭、以及畫面字超過該市場的手機寬度預設。用詞差異另標，不改原句。

## 市場

預設 `--market tw`。也可以用 `hk`、`mo`、`sg`、`cn`。澳門不是香港的別名。寬度是可編輯預設，不是使用率。

## 最後一關

這裡不發佈。每次輸出的最後一行都是：「要發出，還是再改？」
