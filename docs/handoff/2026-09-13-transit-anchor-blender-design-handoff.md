# Transit Anchor Blender 设计完成后交接

更新时间：2026-09-13

当前目标：以 Blender 完整设计包作为可评审的视觉与几何材料，进入“最小变量 patch、Blender review、样机测量、人工 EvidenceReview、再决策”的循环。

## 当前状态

- 数据库：output/experience/transit-anchor-complete-r2/case.db
- 当前候选：scaffold-r1-1.iter-d53a8eee13e0.iter-0f812cd910ad.iter-820dc8412b30.r1
- 当前模型：scaffold-r1-1.model.r12
- 当前阶段：structured_design（Blender draft pending human confirmation）
- 场景策略：scenario-policy-52cf3ff69b8e.r1
- provider：blender，draft 已生成，待人工确认
- prototype evidence：none
- validation protocol：planned

## Blender 设计包

目录：output/experience/transit-anchor-strap-release-r1/blender/design-tool-request-27974b2860c7-onzauykl/

核心资产：design.blend、design.glb、render-2d.png、review-wearer_side.png、review-underside_strap.png、review-stop_control_access.png、review-bystander_state_edge.png、scene.py。

配套文件：output/experience/transit-anchor-strap-release-r1/model-blender-draft.md、human-visual-review.md、portfolio.json、portfolio.md、asset-manifest.json。

物理验证模板：`output/experience/transit-anchor-strap-release-r1/round2-validation-preregistration.md`、`examples/transit-anchor-round2-prototype-run-template.json`、`examples/transit-anchor-round2-measurement-observations-template.json`。模板已通过 Pydantic schema 校验，但尚未导入数据库。

本轮 request/result：design-tool-request-27974b2860c7 / design-tool-result-05a5f31b9aa9；对应 DesignToolRun 为 design-tool-run-7b16ddae32f0.r1，confirmation=pending。`asset-manifest.json` 保存相对路径、大小和 SHA-256；绝对路径只保留在数据库生成记录中。

人工视觉 review：`human-visual-review.md`。结论：`no_blocking_visual_issue_identified`；split band 表达清楚，lift-tab 可能勾挂、底面纹理可能增加压力，均保留为 exploratory 风险；原有 stop path 未见视觉回归。该 review 不确认 geometry，不产生 prototype evidence。

## 当前设计

低轮廓 dorsal-wrist pod；Round 2 split strap、low-profile lift-tab release、anti-rotation underside texture markers；private haptic short bounded pulse；wearer-facing state edge；side-flush guarded recessed press-hold with raised front/back shoulders、650 ms hold target；no response terminates routine event。

仍未验证：精确尺寸、重量分布、表面摩擦、触觉检出率、真实用户偏好、长期可靠性。

Blender、GLB、PNG 和 review views 都是 derived review material，不能证明尺寸、舒适度、贴合、运动稳定性、用户偏好或 prototype evidence。

## 后续方向

### Round 1：停止路径

问题：单手可用、扶杆、携包和注意力分散时，用户能否可靠停止 routine intervention，同时避免误触？

只改 control.cancel_action。建议输入：examples/transit-anchor-next-stop-control-patches.json。

测量：stop completion rate、completion time、false activation rate、failure reason，以及双手不可用阶段是否正确 suppress/defer/timeout。

### Round 2：表带与快拆

问题：袖口、汗湿、扶杆和携包条件下，表带是否减少滑移/旋转，同时仍可快速拆卸？

只改 wearable.attachment_strategy。建议输入：examples/transit-anchor-next-strap-release-patches.json。

测量：displacement、rotation、one-hand release time、snag/false activation、短时不适。

### Round 3：触觉与隐私

问题：private haptic 是否能在振动、袖口、汗湿下被佩戴者检出，同时不向旁观者泄露私人内容？

在 Round 1 和 Round 2 没有 blocking 风险后，再改变 feedback.modality、feedback.timing 或 device.visible_state。

## 下一步命令

查看当前 r12 模型与 Round 2 作品集：

python -m psyteardown.cli design-portfolio --db output/experience/transit-anchor-complete-r2/case.db --model-id scaffold-r1-1.model --out output/experience/transit-anchor-strap-release-r1/portfolio.md --format md --case-id transit-anchor-strap-release-r1

完成物理样机后，使用 `prototype-import` 导入运行和原始测量，再用 `prototype-review` 由人工确认；不要把 Blender 资产直接当作 evidence。

## 下一次对话建议

视觉 review 已完成且无 blocking 视觉问题。下一次不要重复生成 Round 2 revision；从
`round2-validation-preregistration.md` 和两个 JSON 模板开始，填写真实的 device build、
participant scope、conditions、测量方法和采集值。完成实体样机后执行：

1. `prototype-import` 导入 PrototypeRun 与 MeasurementObservation（结果保持 draft）；
2. 核对条件、方法、缺失值和原始文件 hash；
3. 通过 `prototype-review` 由人工选择 observation IDs 和 evidence level。

在真实 run 导入前，`prototype evidence` 必须保持 `none`；Blender pending draft 不能被当作样机证据。

## 当前测试

345 passed, 2 skipped（Round 2 design review、策略 replay、虚拟工程预检与作品集投影测试已补齐）

## 本轮实现补充

- Blender 生成器现在会把 `side_flush_guarded_press_hold` 的前后 raised shoulders 作为显式 derived review geometry 输出；它们只服务于 stop-control access 讨论，不代表激活力、尺寸、抗误触或可制造性。
- 旧的 `transit-anchor-complete-r2` 与 `transit-anchor-stop-path-r1` Blender 包仍保留，作为历史 revision；最新 Round 2 评审应使用 `transit-anchor-strap-release-r1` 的 pending draft。
- `prototype evidence` 仍为 none，validation protocol 仍为 planned；Blender 输出不得直接升级为样机证据。
- 物理样机模板已准备好；填写真实 run/observation 后再执行 `prototype-import`，导入仍会保持 draft，只有 `prototype-review` 后才可能产生 evidence。
- `prototype-import` 会拒绝仍含 `REPLACE_ME` / `YYYYMMDD` 的模板占位符；已知 `transit-anchor-physical-validation/v1` run 会自动保存冻结 protocol snapshot，并在写入前检查 measure/condition、asset 引用和重复 revision。
- 当前没有真实样机数据；已增加 `virtual-validate` 与 `examples/transit-anchor-round2-virtual-validation-input.json`，输出 `virtual-validation-r1.md`。它只计算声明假设下的一阶机械估算，`evidence_level=none`，不写入 prototype run/observation/review。
- `design-portfolio --virtual-validation <report.json>` 会把预检作为独立的非证据章节投影；作品集仍显示 `Prototype runs: 0`、`Evidence level: none`。
- Round 2 Blender draft 已通过 `design-review` 确认，生成模型 revision `scaffold-r1-1.model.r13`（`geometry_ready`）；原始 pending run 保留为 `.r1`，确认 revision 为 `design-tool-run-7b16ddae32f0.r2`。
- 已生成 `asset-manifest-r2-confirmed.json` 与 `human-visual-review-r2-confirmed.md`；确认范围仅为 design/portfolio 派生材料，`prototype evidence` 仍为 `none`。
- 已生成 `scenario-policy-r2-replay.json/.md`，覆盖单手停止、无响应超时、情境纠正和撤回 permission 四条演练轨迹，结果为 `pass`，但仍是策略控制流结果而非用户证据。
