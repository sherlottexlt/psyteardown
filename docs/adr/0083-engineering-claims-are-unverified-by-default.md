# 工程声明默认未验证且不参与候选优先

## Status

accepted

成本、可制造性、续航、耐久和合规统一建模为 EngineeringClaim。AI 生成候选中的声明默认为 unverified；可信数据表或计算说明可成为 source_supported，只有适用实测/工程分析才是 measured 或 Verified Compliance。未验证声明不能作为候选优先依据；对应硬约束但缺证据时进入 explore，明确声明不满足导入阶段约束时 generation_invalid。系统只生成验证清单，不从造型、材料名称或设计叙事推断工程结论。
