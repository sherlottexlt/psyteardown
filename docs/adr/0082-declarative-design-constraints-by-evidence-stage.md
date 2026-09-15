# 非体验约束使用声明式模型并区分声明与实测

## Status

accepted

重量、尺寸、成本、续航和操作等限制使用 DesignConstraint 声明，包含 field_path、白名单 operator、value、unit、tolerance、evidence_required、check_stage 和 failure_status。导入阶段可确定的失败产生 generation_invalid；需要事实确认的约束在 facts_frozen 检查；只有样机才能验证的约束在 L0/L1 标记 explore。声明值与实测值分开，满足声明只产生 Declared Compliance，不等于物理验证。这样避免 LLM 自由解释“轻量”“低成本”等模糊要求。
