# 心理驱动型产品拆解 Agent · v5 设计文档

- 日期:2026-07-16
- 状态:已通过设计评审,待用户确认 spec
- 依赖:v1 + v2 + v3 + v4(已合并到 main)。本文档仅覆盖 **v5**。

---

## 1. 背景与目标

三层记忆架构已完成(v2 情景、v3 语义、v4 程序性)。v4 的元认知靠**跨案例统计**学策略;v5 补上元认知的另一半:**单案例自评(self-critique)**——系统在每次拆解后立刻反思"这一次拆得怎么样",把反思结构化存档,并通过双通道接入 v4 已有的策略学习闭环。

### v5 成功标准

1. `analyze --self-review`(默认关):拆解完成后追加一次 LLM 自评,结果存入案例、渲染进报告。
2. `psyteardown review <case_id>`:对历史案例补做自评(覆盖旧自评);`--to-reflect` 把自评的改进建议直接喂给 v4 reflect 管道生成策略候选(仍走人工审批)。
3. 自评结构化:`score`(0-1 总分)+ `strengths`(亮点)+ `weaknesses`(缺陷:置信虚高/证据薄弱/疑似遗漏)+ `suggestions`(可转策略的改进建议)。
4. **双通道闭环**:① `strategize` 的跨案例统计摘要带上各案例自评信号(有则带,无则略);② `review --to-reflect` 单案例建议直达策略候选。
5. pipeline 零改动(自评发生在拆解之后,由 CLI 编排);全部核心逻辑离线可测(FakeProvider)。

### 明确不做(YAGNI,后置)

- 自改写 step prompt(v6 候选)
- 真改 step2 检索逻辑
- 按 score 自动筛选/降权低质案例(先积累数据)
- 自评的自评(无限递归打住)

---

## 2. 关键决策(已确认)

| 维度 | 决策 |
|------|------|
| v5 主体 | 单案例自评(自改写 prompt、真改 step2 后置) |
| 触发时机 | `analyze --self-review` opt-in(默认关)+ 独立 `review <case_id>` 命令 |
| 输出形态 | 评分 + 亮点 + 缺陷 + 改进建议(结构化 CaseReview) |
| 存储 | 案例内嵌:`Case.review: CaseReview \| None`(存进 case_json,零迁移) |
| 闭环 | 双通道:自评信号进 strategize 摘要 + `review --to-reflect` 直达 reflect 管道 |
| 子系统归属 | 新建 `review/` 目录(方案 A);pipeline 零改动 |

> 存储取舍:CaseStore 整体存 `case_json`,在 Case 模型加可选字段即等效"加列"——旧库读出时 Pydantic 自动填 None,**不改表结构、不写迁移**,同生命周期、同 id、一处查询。

---

## 3. 架构

```
src/psyteardown/
├── review/                      # 新:元认知——单案例自评
│   ├── __init__.py
│   ├── models.py                # CaseReview
│   └── critic.py                # review_case:拆解结果 → 结构化自评
├── memory/
│   ├── models.py                # 改:Case 加 review: CaseReview | None = None
│   └── store.py                 # 改:加 get_with_embedding(case_id)
├── strategy/
│   └── proposer.py              # 改:_case_brief 带上自评信号(有则带)
├── report/
│   └── render.py                # 改:render_markdown/render_json 加可选 review 参数
└── cli.py                       # 改:analyze --self-review;新 review 命令
```

设计原则:

- **pipeline 零依赖 review**:自评发生在拆解之后,由 CLI 编排——与 v4(需注入 prompt)不同,v5 不碰 steps/orchestrator。
- **review 挂在 Case 上而非 TeardownResult 上**:自评是对结果的元层评价,不属于结果本身;TeardownResult 模型保持纯净,渲染时由 CLI 把 review 作为可选参数传入。

### 端到端流程

```
psyteardown analyze --input p.txt --self-review    # 拆解 → 自评 → 存案例 + 报告加「自评」节
psyteardown review <case_id>                       # 历史案例补评(覆盖旧自评)
psyteardown review <case_id> --to-reflect          # 补评 + 建议直达策略候选(走人工审批)
psyteardown strategize                             # 统计摘要自动带各案例自评信号
```

---

## 4. 数据模型与存储

### CaseReview(review/models.py)

```python
class CaseReview(BaseModel):
    score: float = Field(ge=0, le=1)          # 0-1 总体质量分,越界校验失败(SDK 层重试)
    strengths: list[str] = Field(default_factory=list)    # 亮点:拆得好的地方
    weaknesses: list[str] = Field(default_factory=list)   # 缺陷:置信虚高/证据薄弱/疑似遗漏
    suggestions: list[str] = Field(default_factory=list)  # 改进建议(自然语言,可喂 reflect)
    reviewed_at: str = ""                     # 调用方注入
    model: str = ""                           # 自评用的模型标签
```

`messages.parse` 顶层就是 object,无需 wrapper 模型。

### Case 变更(memory/models.py)

```python
class Case(BaseModel):
    ...                                        # 既有字段不动
    review: CaseReview | None = None           # v5:单案例自评,旧数据自动 None
```

`from_result` 签名不变(review 由 CLI 在自评后赋值再 save)。

### CaseStore 变更(memory/store.py)

新增方法,供 `review <case_id>` 补评时取回原 embedding 做 upsert(避免 O(n) 拉全库):

```python
def get_with_embedding(self, case_id: str) -> tuple[Case, list[float]] | None:
    """按 id 取案例及其向量;不存在 → None。"""
```

补评回写:改 `case.review` 后用既有 `save(case, embedding)` upsert,embedding 原样保留。

---

## 5. 自评器(review/critic.py)

```python
def review_case(provider: LLMProvider, result: TeardownResult, *,
                reviewed_at: str, model_label: str = "") -> CaseReview:
    """把 TeardownResult 摘要喂给 LLM 做批判性自评。单次调用,无案例库依赖。"""
```

- 摘要内容:产品(名称/类型/一句话)、各 mapping 的框架·原则·置信·证据(失败 mapping 标注 error)、体验评估、执行摘要。
- System prompt 立场:批判性审阅者,"宁可挑剔不可捧场";缺陷必须指向具体 mapping 或具体遗漏(哪个框架/心理机制疑似漏拆),不接受空泛表扬;置信度与证据不匹配(证据薄弱却高置信)必须点名。
- `reviewed_at` / `model` 由函数注入返回值(库核心不取当前时间,沿用项目惯例)。

---

## 6. 双通道闭环

### 通道 ①:自评信号流入 strategize(strategy/proposer.py)

`_case_brief` 扩展:某案例若有 `review`,在该行后追加自评信号行——

```
- [a1b2] 某社交App(社交App):hook-model.trigger(置信0.9); ...
  自评 0.6:缺陷=对社交证明的置信虚高; 建议=先核对留存数据再定置信
```

无 review 的案例保持原样(向后兼容,现有 proposer 测试不动)。跨案例归纳因此能看到"哪类产品的拆解反复被自评点出同类缺陷"。

### 通道 ②:review --to-reflect 直达策略候选

自评完成后,把 `suggestions` 拼成复盘笔记文本,调用 v4 现成的 `distill_from_note` → 候选进 `strategy_candidates/`,仍走 `strategies approve` 人工审批。**不新建管道,复用 reflect 全链路**(含 target_step 校验、驳回台账、id 净化)。`suggestions` 为空 → 提示"无改进建议,跳过",不算错误。

---

## 7. CLI 与报告

### CLI 变更

```bash
psyteardown analyze --self-review              # 拆解后追加自评(默认关)
psyteardown review <case_id> [--store PATH] [--to-reflect]   # 历史案例补评(覆盖旧自评)
```

- `analyze --self-review --no-save`:仍执行自评并渲染进报告,只是不落库(打印提示)。
- `analyze` 中自评 LLM 失败:graceful 降级——警告 + 报告照常产出(与 v2 memory 降级同风格)。
- `review` 命令独立跑时 LLM 失败:明确报错(用户显式要求自评,不静默)。
- `review` 不存在的 case_id → 明确报错。
- 沿用隐藏 `--provider` 开关供测试注入 Fake。

### 报告渲染(report/render.py)

- `render_markdown(result, *, review: CaseReview | None = None)`:有 review 时加「拆解自评」节(评分、亮点、缺陷、改进建议各列表);None 时整节省略,输出与 v4 完全一致。
- `render_json(result, *, review=None)`:有 review 时 JSON 顶层加 `review` 键;None 时不加。

---

## 8. 测试策略(TDD,全部离线)

- `review/models`:CaseReview 校验、score 越界拒绝(<0、>1)、默认值 — 纯单测。
- `review/critic`:FakeProvider;mapping 证据/失败标注进 prompt、reviewed_at/model 注入返回值 — 离线。
- `memory`:Case.review 默认 None、旧 case_json(无 review 键)load 兼容、带 review roundtrip、`get_with_embedding` 命中/不存在 — 真实 SQLite 文件。
- `strategy/proposer`:带 review 的案例摘要含自评行、无 review 案例输出不变 — 离线。
- `report`:有 review 渲染「拆解自评」节、无 review 省略且输出不变 — 纯单测。
- `cli`:analyze --self-review 全链路(Fake 注入,自评入库+进报告)、review 补评覆盖旧自评、--to-reflect 生成策略候选、不存在 id 报错、analyze 中自评失败 graceful 降级(monkeypatch 抛错)— 离线。
- 不新增可选 e2e(无新外部依赖)。

---

## 9. 接口预留(v6+)

- CaseReview 可加字段(如分步评分)不破坏兼容。
- 按 score 筛选低质案例:数据已在库里,后续加查询即可。
- 自改写 prompt:自评的 weaknesses/suggestions 正是 prompt 改写的输入信号,管道可复用。
