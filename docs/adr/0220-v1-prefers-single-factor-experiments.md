# V1 正式验证优先单一主要变量

## Status

accepted

V1 的正式 ExperimentPlan 优先指定一个 Primary Manipulated Variable，并保持其他设计、任务、用户和场景条件一致。Factorial Experiment 可以保存、导出或导入外部分析，但必须在预注册中声明因素、水平、交互项和分析族；交互结果默认 exploratory，不能拆成单变量因果结论或直接生成单变量 Design Heuristic。工程上无法拆开的多个变化只能形成 Compositional Design Conclusion。
