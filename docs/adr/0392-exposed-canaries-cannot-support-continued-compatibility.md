# 暴露的 Canary 不能证明持续兼容

## Status

accepted

兼容性验证 canary 一旦被供应商、训练管线或可访问人员知悉，必须标记 `canary_exposed` 并退役，不再计入确认性证据；后续验证使用新的未暴露 canary。暴露后的测试成功只能保留为历史审计，不能证明新后端持续兼容。
