---
name: vp-export
description: >-
  對本機輸出說明做解析度、fps、取樣率和峰值檢查。預設不呼叫 ffprobe，不渲染，不上傳。
---

# vp-export

本檔是這份技能包裡另寫的檢查，不是 Jake Schincariol 的官方專案，也不是從 video-production-skills 複製的。該倉庫沒有授權條款。

```bash
python3 exportcheck.py export.json --preset vertical --json
python3 exportcheck.py --run-ffprobe clip.mp4 --preset horizontal --json
```

`--preset vertical` 是 1080x1920、30 fps、雙聲道 48000 Hz、容器名含 mp4。`horizontal` 是 1920x1080，其餘相同。其他數字用 `--target` 的 JSON。這些是技術預設，不代表某個市場比較適合直式。

`--run-ffprobe` 是可選的。系統裡沒有 ffprobe 就停止，不會安裝。它只讀媒體，參數是固定的，不經 shell。預設請交已經存好的 JSON。

沒有 `audio.peak_dbfs` 會標沒量過。報告用 `--out` 寫入時，檔案已存在就停，除非加上 `--overwrite`。

## 市場

預設 `--market tw`。也可以用 `hk`、`mo`、`sg`、`cn`。解析度不隨市場改變。澳門不是香港的別名。

## 最後一關

這裡不發佈。每次輸出的最後一行都是：「要發出，還是再改？」
