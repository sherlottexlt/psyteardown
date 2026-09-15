# 作用域冲突触发阈值须事前声明

## Status

accepted

Heuristic Scope Adequacy Review 的触发阈值在启发式批准时预先声明，并按合法候选、已确认匹配和独立 Brief/场景计数。连续两个 DesignIteration 冲突占比 ≥20%、至少 3 个独立 Brief/场景重复同一冲突、同一范围连续 ≥3 次同类人工覆盖，或一次确认的安全/隐私/控制权冲突，任一满足即可触发；无效、事实未决或无法判断候选不计分，历史计数只能通过新 revision 修订。
