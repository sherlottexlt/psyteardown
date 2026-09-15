# 共享故障默认影响全部分支

## Status

accepted

共享条件、设备、环境、脚本或分配流程故障默认影响全部分支。只有字段级日志、校准或暴露证据证明某分支条件、参与者暴露、测量和数据链完全独立，才可局部隔离并继续审阅；受影响分支标记 `gate_inconclusive_due_to_upstream_integrity`。未受影响分支的 `supported` 不增加外部独立 lineage，边界不明时整体关闭确认性资格。
