# 正式评测使用开发、验证和轮换保留集

## Status

accepted

合成基准划分 Development、Validation 和 Holdout：开发集允许逐项调试，验证集用于阶段验收但不逐例改规则，保留集在发布运行前不进入 prompt、机制/规则检索或人工调参。模型永远看不到答案字段；查看 Holdout 详细错误后，该版本降级为 Validation，下一次发布补充新 Holdout。数据集增加同义改写、图片顺序、无关细节和单变量变化等扰动，split 版本与哈希随报告保存。这样降低对固定案例的长期过拟合。
