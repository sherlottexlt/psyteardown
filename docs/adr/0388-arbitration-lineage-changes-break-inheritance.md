# 仲裁血缘变更切断独立性继承

## Status

accepted

仲裁服务在同一 revision 内更换后端模型、训练/微调快照、运行基础设施或其他关键上游时，必须标记 `arbitration_lineage_change`，从最后可验证声明起切断独立性继承，并按变更前后建立新 lineage 和时间边界。变更时点不明时使用保守窗口标记 `arbitration_lineage_unknown`；供应商事后补发声明不能自动恢复旧结果。
