---
name: vp-mix
description: >-
  檢查混音計畫的淡入淡出、正增益，以及人聲底下的配樂有沒有讓位。不讀音訊、不渲染。
---

# vp-mix

本檔是這份技能包裡另寫的檢查，不是 Jake Schincariol 的官方專案，也不是從 video-production-skills 複製的。該倉庫沒有授權條款。

```bash
python3 mixcheck.py mix.json --duck-gap 6 --json
```

每一段要有 `id`、`role`（voice、music、sfx、other）、`start`、`end`、`gain_db`。配樂和音效若頭尾都沒有 `fade_in`、`fade_out`，會標硬切。增益高過 0 dB 會標削波風險。

和人聲重疊的配樂，增益要至少比人聲低 `--duck-gap`（預設 6），或自行填 `duck_db` 達到這個數。沒有 `peak_dbfs` 就標「沒量過」，不會當成已通過。

這組數字是可改的技術預設，不是某個製作流程的習慣，也不是聽感分數。

## 市場

預設 `--market tw`。也可以用 `hk`、`mo`、`sg`、`cn`。讓位門檻不隨市場改變。澳門不是香港的別名。

## 最後一關

這裡不發佈。每次輸出的最後一行都是：「要發出，還是再改？」
