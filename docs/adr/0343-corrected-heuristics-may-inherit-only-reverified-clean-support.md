# 修复后的启发式只能继承经复核的干净支持

## Status

accepted

完整性修复后的新 heuristic revision 只有在证明原支持单元的候选、操纵、主要结果、协议语义、独立性和分析可复现性未改变，并重新评估用户变体、测量实施与共享依赖后，才可标记 `inherited_clean_support_after_correction` 并经人工复核。受限/污染/不确定支持不能洗成 `supported_clean`；改变假设、结果、变量映射或范围须新建支持链，外部/盲法前瞻性检验不可跳过。
