# 模型任务按完整输入指纹幂等并保留探索性重跑

## Status

accepted

Job Input Fingerprint 由角色、输入快照、Brief/事实/机制/规则版本、prompt、provider/model/采样参数和资产哈希组成。相同 fingerprint 已有 queued/running Job 时复用任务，已有 succeeded Job 时默认复用结果；用户显式重跑才创建 Exploratory Rerun，不能静默覆盖首次合法输出或 current revision。任何领域输入、知识版本或模型配置变化创建新 fingerprint；纯 UI 设置不重跑。正式评测的重复运行全部进入稳定性统计，不允许挑选最佳一次。
