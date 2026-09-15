# psyteardown 平台 M2 实验规划交接

更新时间：2026-09-14

## 当前状态

M1 已完成：通用证据、观察、体验假设、候选 Critique、SQLite revision
持久化、确定性检查和研究对象 CLI 已可用；全量回归基线为 `349 passed,
2 skipped`。

M2 已开始并完成第一切片：将条件性 `ExperienceHypothesis` 转为可人工审查
的实验规划草案。

## 已实现

- `ExperimentVariable`：自变量、至少两个水平、操纵方式、分配方式。
- `MeasureSpec`：因变量、操作性定义、测量方法、单位、primary 标记和缺失策略。
- `SamplePlan`：目标人群、最小/最大样本范围、分配和纳排标准。
- `StoppingRule`：停止/暂停/继续审查条件及责任人。
- `ExperimentPlan` 扩展：研究问题、控制条件、混淆变量、成功判据、伦理备注、
  生成假设来源。
- `build_experiment_plan`：确定性生成 draft，不生成实验结果。
- `preregister_plan`：完整性检查通过后创建新的 `preregistered` revision。
- Markdown/JSON 导出。
- CLI：
  - `python -m psyteardown.cli experiment-plan --hypothesis <file>`
  - `python -m psyteardown.cli experiment-preregister --input <plan.json>`

## 当前边界

- 默认样本范围 `20–60` 只是规划占位，不是 power analysis 结论。
- 规划器不会招募参与者、运行统计或改变 hypothesis 状态。
- `supported` 仍要求真实实验结果和人工 Result Review。
- Transit Anchor 仍是 `geometry_ready / design-review confirmed /
  physical validation pending`，不能用规划文件替代样机证据。

## 下一步 M2

1. 让计划创建正式的 `HypothesisBinding` 和 `AnalysisFamily`，锁定 primary /
   secondary / exploratory 分层和多重比较政策。
2. 将 `ConditionSnapshot`、对照版本和变量水平建立可追溯 revision lineage。
3. 增加 preregistration amendment 字段级检查；实验开始后只能记录
   `ProtocolDeviation`。
4. 为样本量、停止条件和缺失数据策略增加人工审查 CLI 与测试。
5. 在真实实验数据导入前增加 analysis protocol gate；不在 M2 中自动更新
   `supported` / `rejected`。

## 回归要求

每次 M2 改动后运行：

```powershell
pytest -q
```

同时继续报告 Transit Anchor 的 candidate/model revision、`PrototypeRun`、
`MeasurementObservation`、`EvidenceReview` 数量和 evidence level。
