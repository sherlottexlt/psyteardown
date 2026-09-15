# Canary 仅可因预定义技术失败替换

## Status

accepted

Canary 替换只能由预先定义且与仲裁结论无关的技术失败触发；替换次数、抽样算法和停止规则必须冻结。不得因结果不利或难判而换题；技术失败过多时标记 `canary_execution_integrity_failure`，不能静默删除失败样本。
