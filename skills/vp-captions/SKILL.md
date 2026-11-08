---
name: vp-captions
description: >-
  檢查字幕格的行數、顯示寬度和停留是否短於口播粗估。不產生剪輯點。
---

# vp-captions

本檔是這份技能包裡另寫的檢查，不是 Jake Schincariol 的官方專案，也不是從 video-production-skills 複製的。該倉庫沒有授權條款。

```bash
python3 layout.py captions.srt --market tw --json
```

支援 srt、vtt 和帶 `segments` 的 JSON。預設一格最多兩行，每一行不超過該市場的手機寬度預設。停留若明顯短於 4.5 字／秒的粗估，會標太快。五個市場用同一個速率。

口頭禪、空檔和重拍仍用 `deadair.py`。這個工具不改字幕檔。

## 市場

預設 `--market tw`。也可以用 `hk`、`mo`、`sg`、`cn`。澳門不是香港的別名。寬度是可編輯預設，不是平台字數。

## 最後一關

這裡不發佈。每次輸出的最後一行都是：「要發出，還是再改？」
