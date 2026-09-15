# 分析结果自然语言受确定性数据约束

## Status

accepted

实验数据先由版本化确定性脚本形成 Analysis Result；LLM 只能依据结果字段用白名单语言生成 Constrained Result Summary，保留样本、条件、区间、限制和证据强度，不新增数字、显著性、因果或普遍化表述。摘要与 Analysis Result 不一致时标记 summary_validation_failed，不进入正式报告或 Next Prompt；人工可修改摘要文字但不能修改数值、判据或证据。
