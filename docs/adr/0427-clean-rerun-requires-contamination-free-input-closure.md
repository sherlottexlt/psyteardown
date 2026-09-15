# 干净重跑须完成无污染输入闭合

## Status

accepted

`clean rerun` 必须核验输入、提示、缓存、检索索引、依赖数据、环境变量、模型上下文和输出存储，证明不依赖污染对象；运行须使用新工作区并记录版本、哈希和清理证明。任一依赖无法闭合时标记 `clean_rerun_contamination_uncertain`，不得标记 `clean_rederived`。
