# 心理驱动型产品拆解 Agent · v4 设计文档

- 日期:2026-07-08
- 状态:已通过设计评审,待用户确认 spec
- 依赖:v1 + v2 + v3(已合并到 main)。本文档仅覆盖 **v4**。

---

## 1. 背景与目标

记忆架构三层已完成前两层:v2 情景记忆(案例库 + 向量检索)、v3 语义记忆(框架知识增长)。v4 做**第 3 层:程序性记忆/元认知——拆解策略的自我改进**:系统反思过去的拆解,沉淀"怎么拆得更好"的启发式策略卡,人工审批后按步骤注入未来的拆解流程。

| 层 | 沉淀什么 | 记忆类型 | 版本 |
|---|---|---|---|
| 1 | TeardownResult(案例) | 情景记忆 | v2(已完成) |
| 2 | 全新框架 | 语义记忆 | v3(已完成) |
| 3 | **启发式策略卡** | 程序性记忆 | **v4(本文档)** |

### v4 成功标准

1. `psyteardown strategize`:扫描案例库,从跨案例统计规律(哪些框架在哪类产品高置信命中/总是低置信失败)归纳**候选策略卡**。
2. `psyteardown reflect --note "..."`:把用户自然语言复盘蒸馏成候选策略卡(副入口,同一管道)。
3. 候选经**人工审批**(`strategies list/show/approve/reject`)才生效;驳回有台账防复活(同 v3)。
4. `analyze --use-strategies`(默认关):已批准策略卡按 `target_step` 分发注入——mapping 类进 step3、assessment 类进 step4、retrieval 类以"检索建议"并入 step3(不动 v1 纯代码检索)。
5. `applies_to` 品类条件:策略卡可限定适用的产品类型/品类(空 = 通配)——顺带覆盖"分品类 playbook"。
6. 全部核心逻辑离线可测(FakeProvider);`run_teardown`/steps 向后兼容(新参数默认 None = 原行为)。

---

## 2. 关键决策(已确认)

| 维度 | 决策 |
|------|------|
| 沉淀形态 | 启发式/策略卡(含可选 applies_to);自改写 prompt 后置 v5 |
| 反思来源 | 跨案例模式(主)+ 人工复盘输入(副入口);单案例自评后置 v5 |
| 注入方式 | target_step 枚举分发多步:mapping→step3、assessment→step4、retrieval→并入 step3 提示 |
| 开关 | `--use-strategies` opt-in,默认关;注入文案标注"供参考,独立判断" |
| 存储 | YAML;strategy_candidates/ → strategies/ + 驳回台账(仿 v3 GrowthStore) |

---

## 3. 架构与流程

新增 `strategy` 子系统 + 对 `pipeline`(step3/step4)与 `cli` 最小侵入改动。

```
src/psyteardown/
├── strategy/                    # 新:程序性记忆/元认知
│   ├── __init__.py
│   ├── models.py                # StrategyCard + CardList
│   ├── store.py                 # StrategyStore + StrategyError(仿 v3 GrowthStore)
│   ├── proposer.py              # propose_strategies:跨案例模式提炼(主)
│   ├── distill.py               # distill_from_note:人工复盘 → 候选(副)
│   └── select.py                # select_for:按 target_step + applies_to 选卡拼指引
├── pipeline/
│   ├── steps.py                 # 改:map_features/assess_experience 加 strategy_guidance
│   └── orchestrator.py          # 改:run_teardown 加 strategy_cards,分发到对应步
└── cli.py                       # 改:strategize/reflect/strategies 子命令;analyze --use-strategies
```

### 端到端流程(按需、人工把关,与 v3 同构)

```
psyteardown strategize                      # 案例库 → LLM 归纳 → strategy_candidates/
psyteardown reflect --note "社交产品别漏社交证明"   # 复盘 → 结构化候选(副入口)
psyteardown strategies list / show <id>     # 审阅
psyteardown strategies approve <id>         # → strategies/
psyteardown strategies reject <id>          # 删候选 + 台账防复活
psyteardown analyze --use-strategies        # 已批准卡按 target_step 注入 step3/step4
```

### 关键设计点

- **注入分发**:`select_for` 按 `target_step` + `applies_to` 过滤出"这一步、这个产品适用"的卡拼成短指引;每步只见相关卡 → 边界清晰、可分别测试。
- **默认关 + 防污染**:opt-in 开关;注入文案标注"历史归纳策略,供参考,请结合当前产品独立判断"。
- 候选→审批→注入管道、驳回台账、id 净化全部沿用 v3 经验。

---

## 4. 数据模型、存储与选择器

### StrategyCard

```python
class StrategyCard(BaseModel):
    id: str                       # kebab-case,唯一;做文件名(净化 [A-Za-z0-9_-])
    rule: str                     # 启发式本身
    rationale: str                # 依据(从哪些案例规律归纳)
    target_step: str              # "retrieval" | "mapping" | "assessment"
    applies_to: list[str] = []    # 品类命中词;空 = 通配
    source_case_ids: list[str] = []   # 支撑案例(人工复盘可为空)
    created_at: str = ""          # 调用方注入


class CardList(BaseModel):        # messages.parse 顶层需 object
    cards: list[StrategyCard] = []
```

> 与 v3 不同:候选与已批准**同为 StrategyCard**(卡本身已含审阅所需的 rationale/出处),approve 仅移动文件,无需剥离——比 v3 更简。

### 存储布局

```
.psyteardown/
├── strategy_candidates/<id>.yaml     # strategize/reflect 产出,待审
├── strategies/<id>.yaml              # approve 后
└── strategies_rejected.txt           # 驳回台账(防复活)
```

`StrategyStore(root)` 接口(与 v3 GrowthStore 一一对应):`save_candidate / list_candidates / get_candidate / approve / reject / is_rejected / approved_dir / list_approved`。id 净化 `[A-Za-z0-9_-]`;approve = 写 strategies/ 后删候选;reject = 删候选 + 记台账;save 跳过已驳回 id。

### 选择器(select.py,纯代码)

```python
_VALID_STEPS = ("retrieval", "mapping", "assessment")

def select_for(cards: list[StrategyCard], profile: ProductProfile, step: str) -> str:
    """选出 target_step 命中(retrieval 归入 mapping)且 applies_to 命中当前产品的卡,
    拼成编号指引文本;retrieval 类标注「检索层建议」;无命中 → ''。"""
```

命中判断:`applies_to` 为空 = 通配;否则任一词与 `product_type` 或某 feature 名互为子串即命中(与 v1 检索器同风格)。

### 错误处理

- approve/reject 不存在 id → `StrategyError`;非法 id → `StrategyError`。
- 坏 YAML → 加载时明确报错。
- `target_step` 不在枚举 → proposer/distill 过滤丢弃(模型输出防线)。

---

## 5. 提炼、复盘蒸馏、流水线注入、CLI

### proposer.py(主入口,跨案例模式)

```python
def propose_strategies(
    provider: LLMProvider, cases: list[Case], *,
    created_at: str, min_support: int = 3, max_cards: int = 5,
) -> list[StrategyCard]:
    """把案例统计摘要(product_type + 各 mapping 的 framework·principle
    (confidence, error?))喂给 LLM,归纳启发式。
    过滤:source_case_ids 交真实 id 且 ≥min_support;target_step 合法;空案例→[]。"""
```

### distill.py(副入口,人工复盘)

```python
def distill_from_note(provider: LLMProvider, note: str, *, created_at: str) -> list[StrategyCard]:
    """用户自然语言复盘 → 1..n 张策略卡;source_case_ids 允许为空(豁免 min_support);
    target_step 合法性仍过滤;空 note → []。"""
```

同产出、同候选管道。

### 流水线注入(向后兼容)

```python
def map_features(provider, profile, frameworks,
                 prior_summary=None, strategy_guidance=None): ...
def assess_experience(provider, profile, mappings,
                      strategy_guidance=None): ...

def run_teardown(provider, description, library, *, generated_at,
                 model_label=None, top_n=5, prior_summary=None,
                 strategy_cards: list[StrategyCard] | None = None): ...
```

- `strategy_cards is None` → 与 v1/v2/v3 行为完全一致(既有测试不受影响)。
- 提供时:orchestrator 调 `select_for(cards, profile, "mapping")` → step3;`select_for(cards, profile, "assessment")` → step4。
- 注入文案:「以下是历史归纳的拆解策略,供参考,请结合当前产品独立判断」。

### CLI 变更

```bash
psyteardown strategize [--store PATH] [--min-support 3]      # 跨案例提炼候选(需 LLM)
psyteardown reflect --note "..." [--store PATH]              # 复盘蒸馏候选(需 LLM)
psyteardown strategies list [--store PATH]
psyteardown strategies show <id> [--store PATH]
psyteardown strategies approve <id> [--store PATH]
psyteardown strategies reject <id> [--store PATH]
psyteardown analyze --use-strategies                         # 注入已批准卡(默认关)
```

- strategy 根目录 = `--store` 父目录(与 v3 `_growth_store` 同法)。
- `strategize`/`reflect` 沿用 `--provider` 隐藏开关(测试 fake)。
- 空案例库 `strategize` → 提示先积累案例;LLM/存储失败 → 明确报错(不静默)。

---

## 6. 测试策略(TDD,全部离线)

- `models`:StrategyCard/CardList 校验、默认值 — 纯单测。
- `store`:save/list/get/approve(移动)/reject(+台账防复活)/save 跳过已驳回/非法 id/不存在报错 — 真实文件。
- `select`:target_step 分发(retrieval 归入 mapping、assessment 不串台)、applies_to 通配/命中/不命中、空→'' — 纯单测。
- `proposer`:FakeProvider 固定卡;统计摘要进 prompt、min_support 过滤、幻觉 case_id 丢弃、非法 target_step 丢弃、空案例→[] — 离线。
- `distill`:FakeProvider;note 进 prompt、空 note→[]、source 为空仍保留 — 离线。
- `pipeline`:FakeProvider + strategy_cards;mapping 卡进 step3 prompt、assessment 卡进 step4 prompt、step1 不受影响、None 时与既有行为一致 — 离线。
- `cli`:strategize(monkeypatch LLM)→ list → approve → analyze --use-strategies 全链路;reflect;reject — Fake 注入,不触网。
- 不新增可选 e2e(无新外部依赖)。

---

## 7. v4 明确不做(YAGNI)

- 自改写 step prompt(v5)
- 单案例自评(v5)
- 真正修改 step2 纯代码检索逻辑(retrieval 类先在 step3 提示体现)
- 策略效果自动评估 / A-B 对比
- 策略版本管理/回滚(git 管 `.psyteardown/strategies/`)
- 策略卡之间的冲突检测(审批时人工把关)

接口已为 v5 预留(StrategyCard 可加字段;select_for 可扩展新 target_step;反思机制可复用于自评)。
