# 快照后出现的节点默认隔离

## Status

accepted

撤销传播期间新出现且未收到指定 `revoke` revision 的节点标记 `post_snapshot_execution_surface`，立即禁止处理受影响授权；完成版本回执并纳入节点清单对账后才能解除隔离。节点在快照时不存在不能证明其未受影响。
