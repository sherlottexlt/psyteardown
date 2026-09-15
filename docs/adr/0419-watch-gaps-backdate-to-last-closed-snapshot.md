# 监控缺口须回溯至最近闭合快照

## Status

accepted

inventory watch 缺口的起点清单完整性无法证明时，影响窗口必须回溯到最近一次多源对账闭合的 inventory snapshot；快照后至补偿扫描完成全部标记未知。最近闭合快照也无法确认时，从 revision 开始时间起暂停。
