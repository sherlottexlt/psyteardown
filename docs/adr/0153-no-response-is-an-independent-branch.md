# no_response 不解释为同意或拒绝

## Status

accepted

InterventionEvent 必须将 no_response 与 user_rejected、user_snoozed、user_corrected 和 Feedback Not Detectable 分开建模。无响应不表示同意、拒绝、专注或情境成立；routine/important 默认降级、延后或终止，critical 只有冻结 Brief 明确授权时才可在最大强度内有限升级。缺少无响应策略时事件最多 partial，不能 covered；无响应数据不用于推断情绪或意图。
