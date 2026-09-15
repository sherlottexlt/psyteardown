# MVP 使用外部生成与结构化导入

## Status

accepted

V1 不直接绑定真实商业图像、3D 或 CAD 生成 API。系统导出 Design Prompt Package，用户在外部 AI 设计工具生成候选，再通过 ManualImportGenerator 导入结构化 DesignCandidate；代码同时提供 DesignGenerator 协议和 FakeDesignGenerator 以测试完整闭环。这样优先验证体验评审与反馈能力，并保持生成工具可替换；代价是首版生成步骤需要人工在外部工具完成。
