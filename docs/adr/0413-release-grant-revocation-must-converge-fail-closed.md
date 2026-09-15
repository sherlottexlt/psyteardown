# 恢复授权撤销须收敛并默认拒绝

## Status

accepted

高风险证据出现时，`Release Scope Grant` 通过不可变 `revoke` revision 失效并立即传播到所有执行节点和缓存；校验默认 fail-closed。撤销保留历史，离线缓存不得继续放行；传播不明时标记 `grant_revocation_pending`，暂停或转人工，直到确认收敛。
