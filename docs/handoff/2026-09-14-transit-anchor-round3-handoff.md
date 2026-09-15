# Transit Anchor Round 3 触觉与隐私交接

更新时间：2026-09-14

用途：为下一次对话直接开始 Round 3 设计迭代。本文记录 Round 2 的实际完成状态和 Round 3 的待执行边界；没有把计划中的触觉检出率、隐私结果或实体性能写成已验证结果。

## 权威当前状态

- 数据库：`output/experience/transit-anchor-complete-r2/case.db`
- 当前候选：`scaffold-r1-1.iter-d53a8eee13e0.iter-0f812cd910ad.iter-820dc8412b30.r1`
- 当前模型：`scaffold-r1-1.model.r13`
- 当前阶段：`geometry_ready`
- 当前场景策略：`scenario-policy-52cf3ff69b8e.r1`
- 当前 DesignToolRun：
  - 历史 draft：`design-tool-run-7b16ddae32f0.r1`，`confirmation=pending`
  - 当前确认 revision：`design-tool-run-7b16ddae32f0.r2`，`confirmation=confirmed`
- 当前 prototype records：`PrototypeRun=0`、`MeasurementObservation=0`、`EvidenceReview=0`
- 当前 prototype evidence：`none`
- 当前 validation protocol：`planned`
- 数据库事件/审计记录：`42 / 42`

机器可读的交接断言：`Prototype runs: 0`；`Evidence level: none`。

旧的 `2026-09-13-transit-anchor-blender-design-handoff.md` 是历史交接；其中的 r12/pending 描述已被本文件的 r13/confirmed 状态取代。不要用旧文档覆盖数据库当前状态。

## Round 2 已完成内容

Round 2 的唯一设计变量是 `wearable.attachment_strategy`，从 broad vented strap 改为：

`broad vented split strap with low-profile keyed lift-tab release, anti-rotation underside texture and no protruding clip`

当前结构化设计仍包括：

- low-profile dorsal-wrist pod
- centered proximal to wrist crease
- split strap 两条腕轴向 band
- low-profile lift-tab
- underside anti-rotation texture markers
- side-flush guarded recessed press-hold
- 前后 raised shoulders
- `650 ms` hold target
- no response terminates routine event
- private haptic short bounded pulse
- wearer-facing state edge，不暴露私人内容

Round 2 Blender 资产已由人工确认，可用于设计与作品集展示。确认只证明资产对应当前设计 revision，不证明尺寸、制造、舒适、贴合、稳定、勾挂或用户结果。

## Round 2 资产

主资产目录：

`output/experience/transit-anchor-strap-release-r1/blender/design-tool-request-27974b2860c7-onzauykl/`

包括：

- `design.blend`
- `design.glb`
- `render-2d.png`
- `review-wearer_side.png`
- `review-underside_strap.png`
- `review-stop_control_access.png`
- `review-bystander_state_edge.png`
- `scene.py`

确认与说明文件：

- `output/experience/transit-anchor-strap-release-r1/round2-confirmed-model.md`
- `output/experience/transit-anchor-strap-release-r1/asset-manifest-r2-confirmed.json`
- `output/experience/transit-anchor-strap-release-r1/human-visual-review-r2-confirmed.md`
- `output/experience/transit-anchor-strap-release-r1/portfolio.md`
- `output/experience/transit-anchor-strap-release-r1/portfolio.json`

历史 `asset-manifest.json` 和 `human-visual-review.md` 保留为 pending revision 记录；确认后的使用应以 `*-r2-confirmed.*` 为准。

## 已完成的非实体预检

### 虚拟工程预检

输入：`examples/transit-anchor-round2-virtual-validation-input.json`

输出：

- `output/experience/transit-anchor-strap-release-r1/virtual-validation-r1.md`
- `output/experience/transit-anchor-strap-release-r1/virtual-validation-r1.json`

该预检使用声明假设：主体 `42 × 28 × 8 mm`、质量 `18 g`、接触面积 `11.5 cm²`、表带等效预紧力 `8 N`、快拆力 `6.5 N`、长按目标 `650 ms`。六个通勤代理条件下，一阶位移/旋转/压力/释放时间估算没有超过预设筛选阈值，因此软件预检结论为 `proceed_to_physical_prototype`。

该结论不是实体样机结论。触觉检出、袖口勾挂、长期舒适、皮肤安全、隐私泄漏和可靠性仍是 `not_modelled`，evidence 仍为 `none`。

### 场景策略 replay

输入：`examples/transit-anchor-round2-scenario-replay.json`

策略：`output/experience/transit-anchor-strap-release-r1/scenario-policy-r2-replay.json`

输出：

- `output/experience/transit-anchor-strap-release-r1/scenario-replay-r2.md`
- `output/experience/transit-anchor-strap-release-r1/scenario-replay-r2.json`

四条声明式控制流轨迹均为 `pass`：单手停止、无响应超时、情境纠正、撤回 permission。它只验证确定性状态机，不验证传感器分类、触觉发现、用户偏好或真实控制完成率。

## Round 3 目标

研究问题：

> private haptic 是否能在振动、袖口和汗湿下被佩戴者发现，同时不让旁观者推断私人内容？

Round 3 只允许修改以下变量：

- `feedback.modality`
- `feedback.timing`
- `feedback.confirmation`
- `device.visible_state`

建议保持：

- `feedback.modality=private_haptic`
- 禁止 public audio 作为 routine private content 的 fallback
- wearer-facing state edge 只显示 sensing/active/snoozed 等状态，不显示私人内容
- 无响应仍终止 routine event
- correction 仍进入 `safe_boundary_review`
- 不增加自动重复次数或公共显著性

Round 3 应探索触觉节奏/时机，而不是直接声称检出率。例如可以比较：

1. 单一 `250–300 ms` bounded pulse
2. 两段短脉冲（短间隔、总时长受限）
3. 只在 declared safe boundary 发送一次，错过后不重复

上述是待生成的设计方向，不是已确认的用户偏好或生理最佳值。

## 下一次对话建议执行顺序

1. 创建 Round 3 `VariablePatch` JSON，只改上述触觉/隐私变量。
2. 用 `design-iterate` 从当前候选生成 child candidate 和新的 progressive model；确认旧 geometry/render 层被重置为 `missing`。
3. 用 Blender provider 生成 Round 3 derived draft。
4. 用 `design-review` 确认对应的 pending DesignToolRun；不要重新生成同一个 request/result。
5. 为 Round 3 生成触觉/隐私虚拟预检，明确把检出率和旁观者内容识别率留为 `not_modelled`。
6. 生成新的 policy replay，至少覆盖：safe-boundary 单次信号、无响应、reject/cancel、context correction、bystander-facing state。
7. 更新 portfolio；确认其中同时显示新的 model revision、`Prototype runs: 0` 和 `Evidence level: none`。
8. 运行完整测试。

Round 3 的设计确认命令形式：

```powershell
python -m psyteardown.cli design-iterate `
  --db output/experience/transit-anchor-complete-r2/case.db `
  --candidate-revision scaffold-r1-1.iter-d53a8eee13e0.iter-0f812cd910ad.iter-820dc8412b30.r1 `
  --patches examples/transit-anchor-round3-haptic-privacy-patches.json `
  --provider blender `
  --out output/experience/transit-anchor-round3-r1/iteration-draft.md
```

确认已有 pending provider run 时使用：

```powershell
python -m psyteardown.cli design-review `
  --db output/experience/transit-anchor-complete-r2/case.db `
  --run-id <round3-design-tool-run-id> `
  --out output/experience/transit-anchor-round3-r1/confirmed-model.md
```

## 证据与禁止操作

- 不要把虚拟预检数字写入 `MeasurementObservation`。
- 不要用 Blender/GLB/PNG 作为 prototype evidence。
- 不要创建虚构 participant、device build、raw file hash 或真实测量值。
- 在没有真实物理 run 前，不要运行 `prototype-review` 产生 observed evidence。
- 不要修改或删除 Round 2 历史 revision；Round 3 必须创建 child candidate 和新 model revision。
- 不要用 `git reset --hard`、`git checkout --` 或删除整个 `output/experience`。
- 如果 Round 3 触觉或隐私设计引入 public audio、重复强提醒、不可撤销介入或隐藏状态，应停在 `revise`，不得直接确认。

## 当前测试

最近完整测试：`345 passed, 2 skipped`。

测试覆盖 Round 2 的：

- prototype CLI 模板拒绝和 protocol snapshot
- existing pending DesignToolRun 的确认
- virtual validation
- scenario replay
- portfolio 非证据投影

Round 3 修改后必须重新执行：

```powershell
pytest -q
```

## 交接完成判据

新对话只有在以下项目全部满足后，才能报告 Round 3 设计完成：

- 新 child candidate、VariablePatch、ProgressiveDesignModel revision 已保存。
- 新 Blender draft 与 confirmation 状态可追踪。
- 触觉/隐私设计决策和剩余未知项已写入作品集。
- policy replay 能证明 no-response、cancel、correction 和 single-signal boundary 的控制流不变式。
- 作品集明确显示 `Evidence level: none`、`Prototype runs: 0`。
- `pytest -q` 全部通过。

在这些条件满足前，Round 3 状态应写作 `structured_design` 或 `geometry_ready`，不能写作 prototype validated、observed、supported 或 replicated。
