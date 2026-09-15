# 未登记执行面须纳入撤销收敛

## Status

accepted

未登记的执行节点、缓存或离线副本必须标记 `unregistered_execution_surface`，纳入节点清单并扩大撤销影响分析；无法证明其未缓存或未执行受影响授权时，维持 `grant_revocation_pending`，必要时扩大暂停，不能因未在原清单而排除。
