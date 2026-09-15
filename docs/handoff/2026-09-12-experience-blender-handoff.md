# Experience / Blender 设计闭环交接上下文

日期：2026-09-12

## 当前目标

psyteardown 正在从“文本产品心理拆解”扩展为“未来移动与穿戴产品的体验假设、结构化设计和渐进拟合系统”。当前阶段先用确定性规则、Fake provider 和 Blender blockout 跑通闭环，后续再接真实设计工具/渲染模型。

核心路径：

```text
未来运动场景
  → 初步设计规则
  → 完整结构化产品设计
  → Blender blockout
  → PNG / BLEND / GLB 派生资产
  → 人工确认
  → ProgressiveDesignModel 新 revision
  → VariablePatch / 下一轮设计拟合
```

## 已实现模块

主要目录：`src/psyteardown/experience/`

- `models.py`
  - 不可变 Pydantic domain snapshots
  - `DesignBrief`、`DesignCandidate`
  - `DesignShape`、`DesignComponent`、`DesignSpecification`
  - `MovementPhase`、`FutureMovementScenario`
  - `DesignRuleCandidate`、`DesignRuleSet`
  - `ProgressiveDesignModel`、`ModelLayerStatus`
  - `ReviewItem`、`VariablePatch`、`CandidatePartialOrder`
  - revision、dependency、domain/audit event 类型

- `mobility.py`
  - 未来运动/穿戴场景输入
  - 从运动场景投影初步设计规则
  - 创建渐进模型初始快照

- `providers.py`
  - `ScaffoldDesignGenerator`
  - `FakeDesignGenerator`
  - `FakeReviewReasoner`
  - `FakeClaimJudge`
  - `ManualImportGenerator`

- `adapters.py`
  - `DesignToolRequest` / `DesignToolResult`
  - `DesignToolProvider`
  - `BlenderDesignToolProvider`
  - Blender headless Python scene 生成
  - PNG、BLEND、GLB 输出
  - Blender 5.x Eevee 兼容
  - provider 输出默认视为不可信草案

- `service.py`
  - Brief freeze
  - candidate import
  - facts freeze
  - review / selection / next prompt
  - second round
  - variable repair trace
  - progressive model revision attach

- `sqlite.py`
  - experience revisions
  - current projection
  - domain events
  - audit events

- `render.py`
  - 完整设计 Markdown / JSON
  - ProgressiveDesignModel Markdown

- `scaffold.py`
  - `InitialDesignRequest`
  - `generate_initial_design_batch`
  - `generate_complete_design`
  - 批次 Markdown / JSON 导出

## CLI 调用

生成 5 个完整候选：

```powershell
python -m psyteardown.cli design `
  --input examples/design-request.json `
  --out output/experience/future-wearable.md `
  --db output/experience/future-wearable.db
```

导出给外部设计工具的最小请求：

```powershell
python -m psyteardown.cli design-export-request `
  --db output/experience/future-wearable.db `
  --candidate-revision <candidate_revision_id> `
  --out output/experience/design-tool-request.json
```

使用真实 Blender 生成 blockout：

```powershell
python -m psyteardown.cli design-attach `
  --provider blender `
  --blender-executable D:\blendeer\blender.exe `
  --blender-output-root output/experience/blender-real-v3 `
  --db output/experience/future-wearable.db `
  --candidate-revision <candidate_revision_id> `
  --out output/experience/blender-draft.md
```

人工确认并推进模型层级：

```powershell
python -m psyteardown.cli design-attach `
  --provider blender `
  --blender-executable D:\blendeer\blender.exe `
  --blender-output-root output/experience/blender-real-v3 `
  --confirm `
  --db output/experience/future-wearable.db `
  --candidate-revision <candidate_revision_id> `
  --out output/experience/blender-confirmed.md
```

也可以接收外部工具返回的 JSON：

```powershell
python -m psyteardown.cli design-attach `
  --db output/experience/future-wearable.db `
  --candidate-revision <candidate_revision_id> `
  --result design-tool-result.json `
  --confirm `
  --format json `
  --out output/experience/progressive-model.json
```

## 已验证真实成果

示例请求：`examples/design-request.json`

当前示例是“未来可穿戴 AI 伴行助手”，场景为“拥挤通勤换乘”：

- 交通工具内站立
- 下车步行
- 双手不可用/间歇可用
- 视觉注意力间歇可用
- 公共环境
- 手腕佩戴
- 任务/运动阶段切换

真实 Blender 5.2.1 产物：

- `output/experience/blender-real-v3/.../render-2d.png`
- `output/experience/blender-real-v3/.../design.blend`
- `output/experience/blender-real-v3/.../design.glb`
- `output/experience/blender-real-v3-confirmed.md`

确认后的模型阶段：

```text
structured_design: complete
render_assets: complete
geometry: complete
engineering_spec: unverified
prototype_evidence: missing
```

全量测试最近结果：

```text
299 passed, 2 skipped
```

## 不可违反的边界

- Blender blockout 是派生设计资产，不是事实真值。
- 不从渲染图推断真实尺寸、重量、材质性能、舒适度、运动稳定性或用户结果。
- provider 输出必须先是 draft；只有人工确认后才可标记层级完成。
- `DesignRuleCandidate` 默认是 `candidate`，执行强度只能是 `consider_as_option` 或 `validation_only`。
- 不把运动状态、姿态、速度或路径解释为用户意图、情绪、同意或健康状态。
- 不自动选择唯一最佳候选；保留并列、权衡和 Needs Evidence。
- 不覆盖历史 revision；后续调整创建新 revision。
- 真实模型、视觉模型、前端和数据库迁移仍未接入。

## 新队话开始时优先确认的设计问题

请按需确认，不必一次回答全部：

1. 产品形态：腕戴、耳戴、颈戴、衣物夹具、手持，还是分布式穿戴？
2. 首个重点运动场景：通勤换乘、骑行、跑步、步行导航、社交交谈，还是任务切换？
3. 设计方向：隐私优先、低打扰、可发现性、控制感，还是运动稳定性优先？
4. Blender 下一步希望调整什么：形态比例、佩戴结构、确认/取消交互面、状态灯带、反馈模态，还是相机/材质？
5. 下一轮是否允许保留两个并行方向，还是需要先收敛到单一方向？
6. 是否要把外部渲染图/CAD 导入作为新的 Candidate Facts / Observation 流程，而不是直接推进 geometry_ready？

## 建议下一步

优先做参数化 Blender 迭代：让 `VariablePatch` 能修改以下变量并重新生成新 revision：

- `wearable.form_factor`
- `wearable.body_placement`
- `wearable.attachment_strategy`
- `wearable.contact_area`
- `wearable.mass_distribution`
- `feedback.modality`
- `feedback.timing`
- `feedback.confirmation`
- `device.visible_state`
- `control.cancel_action`

每次调整都应保留：父模型 revision、patch revision、Blender request/result、人工确认状态、渲染/几何资产路径和未解决缺口。
