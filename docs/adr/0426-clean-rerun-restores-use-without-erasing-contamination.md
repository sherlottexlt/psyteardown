# 干净重跑可恢复使用但不抹除污染

## Status

accepted

污染对象只有在使用未污染输入、独立执行环境、冻结参数和可复现日志创建新 revision，并确认关键结果一致后，才能标记 `clean_rederived` 恢复使用。旧 revision 必须保留 `unauthorized_output_contaminated`，不得洗白或作为资格证据。
