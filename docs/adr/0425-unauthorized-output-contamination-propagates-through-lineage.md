# 未授权输出污染沿数据血缘传播

## Status

accepted

未授权输出在隔离前被下游读取时，所有直接或间接依赖的候选、事实、ReviewItem、排序、反馈和实验结果必须标记 `unauthorized_output_contaminated` 并暂停使用。只有独立访问日志证明对象未读取该输出，才可隔离保留；人工回忆或结果相同不构成排除污染的证据。
