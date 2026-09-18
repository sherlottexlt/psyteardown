# psyteardown 平台 M3 AI 设计反馈交接

更新时间：2026-09-14

## 已完成的第一切片

M3 已跑通以下确定性边界：

```text
DesignBrief
  → CandidateGenerator
  → DesignCandidate
  → Critique
  → deterministic rank
  → explicit human selection
  → next-round prompt
```

实现位置：`src/psyteardown/experience/m3_feedback.py`。

- `generate_candidates`：通过现有 `DesignGenerator`/`ScaffoldDesignGenerator`
  生成候选并转成不可变 `DesignCandidate`。
- `critique_candidate`：将候选 declared facts 映射为来源绑定的
  `Observation`/`Evidence` 和条件性 `ExperienceHypothesis`；保留未知、硬风险、
  权衡与可操作变量修改。
- `rank_candidates`：硬风险与未知项优先隔离，最终以稳定 candidate ID 作为唯一
  平局键；没有心理学总分，也不把排序当作批准。
- `select_feedback_candidate`：只有显式人工选择才生成下一轮 prompt。
- `DesignFeedbackSelection`：保存选择、candidate revision、critique、排序和
  prompt JSON 的不可变快照，已加入 SQLite registry。
- `render_feedback_json`：导出候选、Critique、排序与 prompt，便于下游生成器消费。
- `render_feedback_markdown`：生成跨候选比较表和逐候选排序因素，保留风险、
  未知、权衡和可操作修改。
- `build_actionable_patches`：人工选择后把反馈转成 `explore`/`constrain`
  `VariablePatch`；不凭空发明目标值，后续由研究员确认具体修复。
- 冻结 brief 的 M3 bundle 会挂到正式 `DesignIteration`；人工选择会写入
  `CandidatePartialOrder` / `SelectionDecision` / `DesignFeedbackSelection`，非首位候选必须提供 `override_reason`。
- `confirm_feedback_next_prompt` 将确认 patch 写入 `NextDesignPrompt`，并由既有
  `generate_second_round` 生成第二轮候选；CLI 新增 `design-feedback-next-round`。
- `create_experiment_plan_from_feedback` 提供显式的人类 handoff 到 M2：仅保存
  `exploratory` hypothesis 并创建 preregistration draft，绝不从排序自动生成实验结果。

CLI：

```powershell
python -m psyteardown.cli design-feedback --brief brief.json --db feedback.sqlite --out feedback.json
python -m psyteardown.cli design-feedback-select --brief brief.json --feedback feedback.json --db feedback.sqlite --candidate <candidate-id> --out selected.json
python -m psyteardown.cli design-feedback-next-round --brief brief.json --feedback selected.json --db feedback.sqlite --out second-round.json
```

## 重要边界

- 生成和排序不会自动选择候选。
- 硬风险候选不能被普通选择命令绕过。
- 未知物理性能不会被写成事实。
- Hypothesis 默认保持 `exploratory`；真实实验和人工 Result Review 之前不能
  变为 `supported`。
- prompt 明确携带 `do_not_claim`：心理状态不是事实、未测物理性能不是证据、
  系统不自动批准。

## 下一步

继续在真实研究员确认、物理测量和 Result Review 后推进 M2 preregistration；M3
排序本身仍不构成实验结果或 hypothesis support。

## 回归

当前全量测试基线：`371 passed, 2 skipped`。
Transit Anchor 仍为 `geometry_ready / design-review confirmed /
physical validation pending`。
