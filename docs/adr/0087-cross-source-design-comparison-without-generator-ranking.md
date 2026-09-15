# 允许跨来源设计比较但不评价生成模型优劣

## Status

accepted

V1 允许 external_model、human 和 hybrid 候选在同一 DesignBrief snapshot、基准场景、输入契约、事实确认、机制库、规则库和评审版本下参与设计比较。系统记录生成器名称/版本、prompt_package_id 和 human_edits；人工实质修改后创建 Hybrid Candidate，后续结果不归因于原始模型。V1 不据此声称某生成器优于另一生成器，因为未控制生成预算、随机性、重复次数和人工编辑规则。这样支持现实工作流而避免无效模型排行榜。
