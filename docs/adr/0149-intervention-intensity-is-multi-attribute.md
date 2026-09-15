# 介入强度使用模态内多属性表达

## Status

accepted

V1 的 InterventionIntensity 使用 modality 内 salience_level 0–3 与 duration、repetition、persistence、privacy_exposure、attention_capture、user_override_cost、fallback_level 等字段描述，不压缩成跨模态单一分数。不同模态的数字等级不可直接等价；Maximum Intervention Intensity 作为各属性上限，实际候选值由事实确认后检查，缺少关键属性时最多 unknown/explore。更高显著性不自动等于更有效。
