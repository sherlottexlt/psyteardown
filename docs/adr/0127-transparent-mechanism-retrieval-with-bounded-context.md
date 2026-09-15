# 机制检索透明且不等于机制采用

## Status

accepted

Mechanism Retrieval Result 同时作为 ReviewReasoner 的受限上下文和人工界面的透明依据，保存机制卡/适用映射 ID、版本、命中理由、适用/排除边界、混淆变量、测量方式和最低证据要求。ReviewItem 必须记录实际采用的机制与检索候选的差异；被检索不等于被采用，Candidate Mechanism 只能进入 explore 或待审映射，不能直接作为正式机制依据。
