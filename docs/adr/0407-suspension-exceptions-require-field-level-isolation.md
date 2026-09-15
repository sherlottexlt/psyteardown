# 暂停例外须经字段级隔离证明

## Status

accepted

全局暂停期间，只有字段级依赖闭合证明某路径不共享受影响模型、规则、信任链、数据链、选择机会集或关键故障模式，才可继续运行并标记 `isolated_during_suspension`。功能或团队不同不足以证明隔离；无法闭合时保持 `validation-only` 或人工选择。
