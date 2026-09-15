# Provider 输出作为派生资产或草案处理

## Status

accepted

Provider 返回的图片、OCR、裁剪、标注、render、mask 和 embedding 创建 Provider-Derived Asset，保存父资产、provider/model/run、请求快照、输出类型、hash、provenance、隐私和留存信息，不覆盖输入；输入删除/限制时依赖资产传播影响。Provider Structured Output（JSON/Schema）统一视为不可信草案，经过 Schema/引用/规则校验和人工阶段门后才能转换为 Confirmed Observation、ReviewItem 或其他领域 revision；OCR 和候选文字不能改变系统指令。
