# 废弃启发式停止新回灌但保留历史

## Status

accepted

Approved Design Heuristic 进入 deprecated 后，不再被新的 Next Design Prompt 作为 Heuristic Option 注入；尚未发送的提示需要重新投影并经人工确认。已发送提示、候选、评审和实验结果保留，并显示依赖的 heuristic revision，不自动判定历史设计错误。若新证据支持恢复，创建新 Heuristic revision 并重新审批，不能原地恢复旧版本。
