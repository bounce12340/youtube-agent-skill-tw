---
name: vp-assets
description: >-
  檢查本機素材清單有沒有相對路徑、來源和授權標籤。不判斷授權是否合法，不上網。
---

# vp-assets

本檔是這份技能包裡另寫的檢查，不是 Jake Schincariol 的官方專案，也不是從 video-production-skills 複製的。該倉庫沒有授權條款。

```bash
python3 ledger.py assets.json --json
python3 ledger.py assets.json --check-files --root .
```

每一筆要有 `id`、`path`、`source`、`license_label`。路徑必須是相對路徑，不能含 `..`。`license_label` 是你自己寫的標籤，空白才會被標出。工具不把某個詞當成法律許可。

`--check-files` 只看檔案在不在 `--root` 底下。預設不看磁碟。沒有 `--overwrite` 就不會蓋掉已有的報告。

## 市場

預設 `--market tw`。也可以用 `hk`、`mo`、`sg`、`cn`。這項檢查不改市場用詞。澳門不是香港的別名。

## 最後一關

這裡不發佈。每次輸出的最後一行都是：「要發出，還是再改？」
