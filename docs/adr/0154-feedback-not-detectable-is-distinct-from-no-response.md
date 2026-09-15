# feedback_not_detectable 与 no_response 分开处理

## Status

accepted

无法确认用户是否感知反馈时标记 feedback_not_detectable，不能进入 no_response 或自动升级路径。普通事件记录发现性未知，允许低隐私代价的 fallback 并进入发现性实验；critical 只有冻结 Brief 授权且有升级次数/强度上限时才可有限升级，并需安全复核。评审和结果数据区分 detectability_unknown、user_did_not_respond 和 user_rejected；发现性数据不用于推断情绪或意图。
