# DesignVariable 词汇表增量演进且历史 ID 不重写

## Status

accepted

Canonical DesignVariable 只通过新增版本演进；旧 variable_id/value_id 及其语义保留并可标记 superseded。重命名、拆分、合并通过 replacement ID 和人工确认的 mapping；枚举语义变化创建新 value_id，单位变化保存转换公式、精度和原始单位。变量词汇版本进入 Job fingerprint，历史 ReviewItem/Variable Repair Trace 不自动改写；无法可靠映射的跨版本比较标记 uncomparable。
