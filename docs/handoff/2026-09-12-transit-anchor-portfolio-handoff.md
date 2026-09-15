# Transit Anchor 作品集 / 场景状态机 / 样机验证交接

更新时间：2026-09-12

这份文档用于下一次对话直接接续开发。当前仓库已有用户工作区变更，不要使用 destructive git reset/checkout；先阅读本文件和现有 handoff，再在现有 revision 链上继续。

## 一句话结论

产品方向已经从泛化的“未来可穿戴 AI 伴行助手”收敛为：

> Transit Anchor：面向拥挤通勤换乘的低轮廓背侧腕戴伴行器。常规介入优先使用私密、短促、受边界约束的触觉；视觉只表达佩戴者可见的状态；高风险移动阶段抑制 routine 内容；取消、拒绝、纠正和无响应终止都必须保持可追踪。

它是一个结构化设计假设，不是已经验证的硬件产品。Blender blockout、GLB、PNG 和状态机都不能证明尺寸、重量、舒适度、贴合、运动稳定性、触觉检出率、隐私结果或用户偏好。

## 已完成的产品关键变化

### 形态

- 从泛化矩形 wearable / clip / desk stand，收敛到 low-profile rounded dorsal-wrist pod。
- 使用宽、柔性、透气、可逆的表带方向；避免突出式 clip、旋钮和易刮挂结构。
- 质量分布声明为靠近腕轴/前臂中心线；仍需测量，不是工程事实。
- 侧边使用 guarded recessed press-hold 作为盲操作停止路径。
- 常态状态边只表达 active/sensing 等状态，不表达私人内容。

### 反馈与状态

- routine 事件优先 `private_haptic`。
- 高运动、车门、楼梯、横越冲突区域等阶段 suppress/defer routine 事件。
- 安全边界恢复后最多给出一次 bounded private signal。
- no response 不代表接受；routine 事件自动终止。
- reject/cancel 后不自动升级或重复介入。
- context correction 会停止当前事件，并重新要求 permission decision。
- 姿态、路线、速度、运动阶段不能被解释为意图、情绪或同意。

## 已实现的代码能力

### 参数化迭代

主要文件：

- `src/psyteardown/experience/iteration.py`
- `src/psyteardown/experience/service.py`
- `src/psyteardown/experience/models.py`

已支持的 patch 变量：

- `wearable.form_factor`
- `wearable.body_placement`
- `wearable.attachment_strategy`
- `wearable.attachment`（兼容旧 mobility 规则）
- `wearable.contact_area`
- `wearable.mass_distribution`
- `feedback.modality`
- `feedback.timing`
- `feedback.confirmation`
- `device.visible_state`
- `control.cancel_action`

每次 `design-iterate` 会尝试保留：

- parent candidate revision
- child candidate revision
- parent / child ProgressiveDesignModel revision
- VariablePatch revision
- VariableRepairTrace
- Blender request/result
- `DesignToolRun` draft/confirmed 状态

参数化后，旧 `render_assets` 和 `geometry` 会重置为 `missing`，必须重新生成和人工确认。

### Blender blockout

主要文件：`src/psyteardown/experience/adapters.py`

当前 blockout 已包含：

- 低轮廓主体
- 表带环带
- wrist context proxy（明确标注为 derived / non-anatomical scale）
- 上表面确认区
- 侧面停止控件
- wearer-facing status edge

context proxy 只用于讨论佩戴方向、控件可达性和干涉关系，不能当作腕部尺寸或人体工学证据。

### 作品集投影

主要文件：

- `src/psyteardown/experience/portfolio.py`
- `docs/portfolio/README.md`
- `docs/portfolio/transit-anchor-case-study.md`
- `docs/portfolio/transit-anchor-case-study.json`

作品集 JSON 是可持续同步的结构化源；Markdown 是展示投影。当前内容包括：

- 当前产品快照
- baseline → VariablePatch revision → Blender asset → validation plan 演化链
- parent candidate/model 和 patch IDs
- 当前图形资产路径
- 场景状态机
- 样机验证协议
- 未声明和未验证边界

## 当前可复现数据

推荐使用新建的干净 demo 数据库：

- DB：`output/experience/transit-anchor-portfolio-demo/case.db`
- iteration draft：`output/experience/transit-anchor-portfolio-demo/iteration-draft.md`
- portfolio MD：`output/experience/transit-anchor-portfolio-demo/portfolio.md`
- portfolio JSON：`output/experience/transit-anchor-portfolio-demo/portfolio.json`
- Blender 输出目录：`output/experience/transit-anchor-portfolio-demo/blender/`

当前 demo 的核心 model：

```text
model_id: scaffold-r1-1.model
current model revision: scaffold-r1-1.model.r3
current child candidate: scaffold-r1-1.iter-db6118ebbd16.r1
provider result: draft / unconfirmed
```

示例 patch：`examples/transit-anchor-patches.json`

请求示例：`examples/design-request.json`

## 常用命令

### 生成基础候选批次

```powershell
python -m psyteardown.cli design `
  --input examples/design-request.json `
  --db output/experience/future-wearable.db `
  --out output/experience/future-wearable.md
```

### 参数化生成子候选和新的 blockout

```powershell
python -m psyteardown.cli design-iterate `
  --db output/experience/future-wearable.db `
  --candidate-revision <parent-candidate-revision> `
  --patches examples/transit-anchor-patches.json `
  --provider blender `
  --blender-executable D:\blendeer\blender.exe `
  --blender-output-root output/experience/blender-next `
  --out output/experience/iteration-draft.md
```

只创建结构化子 revision、不生成 provider 资产：

```powershell
python -m psyteardown.cli design-iterate `
  --db output/experience/future-wearable.db `
  --candidate-revision <parent-candidate-revision> `
  --patch examples/transit-anchor-patches.json `
  --provider none
```

### 人工确认 provider draft

```powershell
python -m psyteardown.cli design-attach `
  --db output/experience/future-wearable.db `
  --candidate-revision <candidate-revision> `
  --provider blender `
  --blender-executable D:\blendeer\blender.exe `
  --confirm `
  --out output/experience/confirmed.md
```

`--confirm` 只确认派生资产属于该设计 revision；它不会把 engineering spec 或 prototype evidence 自动变成 complete。

### 生成作品集

```powershell
python -m psyteardown.cli design-portfolio `
  --db output/experience/future-wearable.db `
  --model-id <model-id> `
  --format md `
  --out docs/portfolio/transit-anchor-case-study.md

python -m psyteardown.cli design-portfolio `
  --db output/experience/future-wearable.db `
  --model-id <model-id> `
  --format json `
  --out docs/portfolio/transit-anchor-case-study.json
```

## 当前场景状态机

状态：

```text
monitoring
  → suppressed       hazard phase entered
  → deferred         routine event arrives while hazard remains
  → private_signal   safe boundary declared
  → awaiting_response
  → terminated       reject / cancel / timeout
  → monitoring       new independent event + new permission
```

错误情境 correction 从 `awaiting_response` 进入 `safe_boundary_review`，不会直接恢复原推断。

当前状态机仍主要是 portfolio/domain projection，不是运行时传感器分类器，也不是完整的 critical-event policy engine。

## 当前样机验证协议

优先测量：

1. 表带位移与旋转
2. 扶杆、包带、碰撞时的误触率
3. 一手可用时的停止完成率和完成时间
4. 双手不可用时的抑制/超时是否正确结束
5. 车辆振动、衣袖、汗湿条件下的触觉检出率
6. 接触压力、温升和短时刺激信号
7. 快速拆卸时间与可达性
8. 状态可见但私人内容不可被旁观者推断
9. 下车阶段对环境扫描与导航任务的干扰

协议明确不声称：

- 长期舒适度
- 医疗安全
- 防水/Ingress 保护
- 制造耐久性
- 真实事故或伤害降低
- 用户意图、情绪、健康状态或同意

## 下一阶段优化路线

### P0：把状态机变成可执行的领域策略

新增 `ScenarioPolicy` / `InterventionDecision` 或等价模型，使每个 movement phase 可以确定性地产生：

- suppress / defer / allow
- 允许的 feedback modality
- 最大 intervention intensity
- response timeout
- no-response outcome
- correction outcome
- 离线 stop 行为

这一层完成后，portfolio 中的状态机不只是说明文档，而能被测试和运行时策略复用。

### P0：把样机测量变成持久化证据

建议新增：

- `PrototypeRun`
- `MeasurementObservation`
- `EvidenceReview`
- `PrototypeAsset`

并支持：

- 预注册 protocol revision
- 条件和设备 revision
- 原始文件 hash
- 测量方法和单位
- participant/context scope
- 缺失和技术失败原因
- 人工 review 状态
- 只有人工确认后，才允许把 validation protocol 从 `planned` 提升为 `observed` 或更高证据状态

### P1：外部 CAD / 渲染图导入流程

建立：

```text
ExternalAsset
  → ObservationDraft
  → HumanConfirmation
  → CandidateFacts / Geometry Evidence
```

必须保存 asset hash、provider、request、观察事实、不可观察项和确认状态，禁止直接从 GLB/PNG 推断工程尺寸或舒适度。

### P1：Blender 多视图与结构表达

增加：

- 佩戴状态侧视
- 佩戴状态底视
- 侧面停止控件可达性
- 表带闭合与快速拆卸
- wearer-facing / bystander-facing 状态灯对比
- 车门/站台/扶杆的简化干涉场景

保持每个视图都标记为 derived review material。

### P1：patch 冲突与 scope

补强：

- 同一变量、重叠 scope 的冲突检测
- `must / should / explore` 执行差异
- stale result 与 current revision 冲突
- patch adopt / partial / not adopted 的实际比较
- `wearable.attachment` 与 `wearable.attachment_strategy` 的 canonical alias 收敛

### P2：作品集呈现质量

- 把绝对 Windows 路径转换为相对作品集路径
- 自动生成图形时间线和 before/after 对照页
- 仅显示当前方向或展开完整 revision tree
- 加入“设计决定 → 图形变化 → 验证问题”的三列对照
- 为每个资产生成缩略图和 hash

### P3：工程与生产信息

在 P0/P1 验证证据充分前，不要急着补精确尺寸、材料性能、IP 等级或制造成本。后续再引入 CAD、材料属性卡、工程规格和制造假设的独立 revision。

## 推荐的新对话第一步

优先执行：

> 实现 `PrototypeRun + MeasurementObservation + EvidenceReview`，把当前验证协议从静态 portfolio 文档升级为可导入、可人工确认、可追踪的 evidence workflow；不要把任何 Blender 结果自动提升为 prototype evidence。

完成后再把 portfolio JSON 的 `validation_plan.status` 从 `planned` 按确认后的证据投影为 `observed` / `exploratory`，并保留历史 protocol revision。

## 最后一次测试结果

```text
305 passed, 2 skipped
```
