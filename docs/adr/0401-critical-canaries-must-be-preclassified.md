# 关键 Canary 须事前分类

## Status

accepted

兼容性 revision 开始前，独立方法审阅者必须依据 canary 失败对安全、完整性、关键顺序、资格或候选纳入/排除的潜在影响，将 canary 分类为关键或普通并冻结在预注册中。不能按测试结果事后降级关键性；普通 canary 后来被证明影响关键决策时，必须触发 criticality reclassification 和影响分析。
