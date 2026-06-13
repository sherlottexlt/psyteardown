# 心理驱动型产品拆解 Agent —— v1 设计文档

- 日期:2026-06-13
- 状态:已通过设计评审,待用户确认 spec
- 范围:本文档仅覆盖 **v1**。v2 / v3 各自有独立 spec。

---

## 1. 背景与目标

构建一个"心理驱动型产品拆解 Agent 工具":基于心理学理论自动拆解任意产品(App、网页、硬件等)的功能与体验,产出可解释、可信、结构化的拆解结果。

完整产品愿景包含多个子系统(心理学知识库、拆解引擎、Skill 封装、多接口 Agent),它们构成一条流水线而非各自独立。为避免一次性铺开,按依赖关系分阶段交付:

- **v1(本文档)**:种子知识库 + 拆解引擎 → 结构化报告;库为核心 + 薄 CLI。
- **v2(后续)**:知识库"越用越厚"的沉淀闭环 + 检索增强。
- **v3(后续)**:把重复拆解抽象成可复用 Workflow → 封装 Skill → 多接口 Agent(API/聊天)。

### v1 成功标准

1. 给定一段产品文字描述,能产出一份结构化拆解报告(Markdown 与 JSON 两种格式)。
2. 报告中每条心理学结论都带**框架出处**与**置信度**,并单列**伦理/暗黑模式**提示。
3. 知识库预置 6–8 个经典框架,以人可读的 YAML 存储,可手改、可扩展。
4. 拆解内核是干净的库,CLI 仅为薄入口;核心逻辑可脱离真实 LLM API 测试。
5. LLM 通过可插拔的 provider 接口调用,默认实现为 Claude。

---

## 2. 关键决策(已确认)

| 维度 | 决策 |
|------|------|
| v1 核心 | 种子知识库 + 拆解引擎 → 结构化报告 + 库核心 + 薄 CLI |
| 产品输入 | 文字为主,架构预留抓取 / 多模态扩展点 |
| 知识库形态 | 精选心理学框架,结构化入库(YAML) |
| 对外接口 | 库为核心 + 薄 CLI |
| 实现语言 | Python |
| LLM | 可插拔 provider 抽象,v1 默认实现 Claude |
| 引擎架构 | 方案 B:显式多步流水线 |

---

## 3. 整体架构与模块边界

核心原则:**拆解内核是一个干净的库,CLI 只是薄入口**。每个模块单一职责、接口清晰、可独立测试。

```
psyteardown/                  # Python 包(库内核)
├── kb/                       # 知识库子系统
│   ├── models.py             #   Framework / Principle 数据模型
│   ├── loader.py             #   从 data/frameworks/*.yaml 加载、校验
│   └── retriever.py          #   按产品类型/功能选相关框架(v1:标签+关键词;预留向量检索接口)
├── pipeline/                 # 拆解流水线(方案 B 的 5 步)
│   ├── steps.py              #   每步一个函数:输入 dataclass → 输出 dataclass
│   ├── orchestrator.py       #   串联 5 步,产出 TeardownResult
│   └── schemas.py            #   各步输入/输出的结构化 schema
├── llm/                      # LLM provider 抽象
│   ├── base.py               #   LLMProvider 接口
│   └── claude.py             #   v1 默认实现
├── report/                   # 报告渲染
│   └── render.py             #   TeardownResult → Markdown / JSON
└── cli.py                    # 薄 CLI:解析参数 → 调内核 → 输出

data/frameworks/              # 种子知识库(YAML,人可读可改)
tests/                        # 单测(KB 加载、检索、各步、渲染均可脱离真实 LLM 测)
```

### 数据流(一次拆解)

```
产品描述(文本/文件)
   → orchestrator
       → step1 解析 → step2 检索KB → step3 逐功能映射 → step4 体验评估 → step5 综合
   → TeardownResult(结构化对象)
   → report.render → Markdown / JSON
```

### 关键设计点

- `pipeline` 依赖 `llm` 接口与 `kb`,但不依赖具体 provider —— 测试时注入假 provider。
- 每步是"输入 dataclass → 输出 dataclass",LLM 调用经注入的 provider 完成,因此**不调真实 API 也能测**编排逻辑。
- `kb.retriever` v1 用标签/关键词匹配,接口签名预留将来换向量检索。

---

## 4. 知识库数据模型

每个心理学框架是一个 YAML 文件(`data/frameworks/*.yaml`),人可读、可手改、可 PR。加载时校验成 `Framework` 对象。

### YAML 示例

```yaml
# data/frameworks/fogg-behavior-model.yaml
id: fogg-behavior-model
name: Fogg 行为模型
category: motivation            # motivation / persuasion / cognition / emotion / habit ...
summary: 行为 = 动机 × 能力 × 提示,三者同时满足才发生。
tags: [行为触发, 习惯养成, 转化]
principles:
  - id: trigger
    name: 提示(Trigger)
    description: 在动机与能力都足够时,需要一个提示来触发行为。
    look_for: [推送, 红点, 空状态引导, 按钮显著性]
  - id: ability
    name: 能力(Ability)
    description: 降低完成行为所需的努力/成本。
    look_for: [一键操作, 默认值, 减少步骤]
references:
  - "Fogg, B.J. (2009). A behavior model for persuasive design."
ethics_notes: 可被用于暗黑模式(如制造虚假紧迫),拆解时需标注。
```

### 数据模型

```python
@dataclass(frozen=True)
class Principle:
    id: str
    name: str
    description: str
    look_for: list[str]          # 拆解时的观察线索

@dataclass(frozen=True)
class Framework:
    id: str
    name: str
    category: str
    summary: str
    tags: list[str]
    principles: list[Principle]
    references: list[str]
    ethics_notes: str | None
```

### 设计要点

- `look_for` 把抽象理论转成"在产品里具体找什么",直接喂给 step3,提升拆解的具体度与可解释性。
- `references` 强制每个框架有出处,降低 LLM 编造理论的风险。
- `ethics_notes` 支撑 step4 的暗黑模式/伦理评估。
- **v1 种子库预置约 6–8 个框架**:Fogg 行为模型、Hook 上瘾模型、Cialdini 说服六原则、自我决定论(SDT)、峰终定律、认知偏误精选、心流(Flow)。覆盖动机/说服/认知/情绪/习惯几大类。

---

## 5. 拆解流水线(方案 B:5 步)

每步为 `输入 dataclass → 输出 dataclass`,LLM 调用通过注入的 provider 完成。

### Step 1 · 解析产品 → 功能/体验清单

输入:原始产品描述文本。输出:

```python
@dataclass
class Feature:
    name: str
    description: str
    user_goal: str

@dataclass
class ProductProfile:
    name: str
    product_type: str            # App / 网页 / 硬件 ...
    one_liner: str
    features: list[Feature]
    touchpoints: list[str]       # onboarding、推送、付费墙 ...
```

本步只做"看清产品有什么",不涉及心理学。

### Step 2 · 检索相关框架(纯代码,无 LLM)

输入:`ProductProfile`。`kb.retriever` 按 `product_type` + features/touchpoints 关键词匹配 framework 的 `tags`,返回 Top-N 个 `Framework`。可解释、可测、不烧 token。

### Step 3 · 逐功能映射到心理学机制

对每个 feature/touchpoint,带着检索到的框架问 LLM:用到哪个框架的哪条 principle、对应哪个 `look_for` 线索、为何有效、置信度。输出:

```python
@dataclass
class Mapping:
    feature: str
    framework_id: str
    principle_id: str
    rationale: str               # 为什么这条原则适用
    evidence: str                # 产品里的具体体现
    confidence: float            # 0–1,低置信度在报告里标注
    error: str | None = None     # 该 feature 映射失败时记录,不中断整次拆解
```

### Step 4 · 整体体验评估

输入:`ProductProfile` + 所有 `Mapping`。评估动机/阻力、情绪曲线、习惯回路,并基于框架 `ethics_notes` 标注暗黑模式/伦理风险。

```python
@dataclass
class ExperienceAssessment:
    strengths: list[str]
    friction_points: list[str]
    ethics_warnings: list[str]
    opportunities: list[str]
```

### Step 5 · 综合

汇总为 `TeardownResult`(见第 6 节),并生成 executive summary。

### 编排与健壮性

- `orchestrator` 顺序执行,各步输出留痕(便于 v2 沉淀 KB、debug)。
- 单个 feature 的 step3 失败标记为 `error` 并继续,不炸掉整次拆解。
- 每步 LLM 调用走 provider 的 `structured_complete`(强制 schema),解析失败重试。

---

## 6. 拆解结果与报告输出

### 结构化产物

```python
@dataclass
class TeardownMeta:
    model: str
    generated_at: str            # 时间戳由调用方传入/渲染时注入
    elapsed_seconds: float
    tokens_per_step: dict[str, int]

@dataclass
class TeardownResult:
    product: ProductProfile
    frameworks_used: list[str]          # 引用的框架 id(可追溯)
    mappings: list[Mapping]
    assessment: ExperienceAssessment
    executive_summary: str
    meta: TeardownMeta
```

### 两种输出格式(同一对象,两套渲染)

- **JSON**:`TeardownResult` 原样序列化 → 供自动化系统 / 未来 API 消费。
- **Markdown**:人读报告,结构:
  1. **概述** — 产品一句话 + executive summary
  2. **产品画像** — 类型、核心功能、关键触点
  3. **逐功能心理学拆解** — 按 feature 分组,每条:`功能 → 框架·原则 → 产品中的体现 → 为什么有效`;低置信度打 ⚠️
  4. **整体体验评估** — 动机/阻力、情绪曲线、习惯回路
  5. **⚠️ 伦理 / 暗黑模式提示** — 单列一节,基于框架 `ethics_notes`
  6. **机会点** — 可改进/可借鉴建议
  7. **附录** — 引用框架列表 + 出处(references)

### 设计要点

- 报告**始终带出处与置信度** —— "心理驱动"工具的可信度命脉,避免变成"煞有介事的瞎编"。
- 伦理提示**单独成节**,呼应产品定位的责任感。
- `meta` 记录各步 token/耗时,为 v2 的成本优化与 KB 沉淀留数据。

---

## 7. LLM 抽象、CLI、错误处理与测试

### LLM provider 抽象

```python
class LLMProvider(ABC):
    @abstractmethod
    def structured_complete(self, prompt: str, schema: type[T], *, system: str | None = None) -> T:
        """返回校验过的 schema 实例;解析失败由实现内部重试。"""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str: ...
```

- v1 实现 `ClaudeProvider`(默认)。pipeline 各步只依赖此接口,**不 import 任何具体 SDK**。
- 测试用 `FakeProvider`(返回固定结构)→ 整条流水线脱离真实 API 跑通。
- 模型 id / API key 走配置(环境变量 + 可选配置文件),不硬编码。**具体模型 id 在实现阶段查 `claude-api` 技能确认到最新。**

### CLI(薄入口)

```bash
psyteardown analyze --input product.txt --format md   --out report.md
psyteardown analyze --input product.txt --format json --out result.json
psyteardown kb list                      # 列出已加载框架
psyteardown kb show fogg-behavior-model   # 查看某框架详情
```

CLI 只做:读输入 → 调 `orchestrator` → 调 `report.render` → 写输出。零业务逻辑。

### 错误处理

- 输入为空/无法解析 → 友好报错,非栈追踪。
- 单 feature 映射失败 → 标 `error` 继续,报告里如实标注(不假装成功)。
- LLM 结构化输出解析失败 → provider 内重试 N 次,仍失败则该步降级并记录。
- API key 缺失 → 启动即明确提示。

### 测试策略(TDD)

- `kb`:加载/校验(坏 YAML 报错)、retriever 匹配正确框架 —— 纯单测。
- `pipeline`:用 `FakeProvider` 测每步 + 编排,含失败降级路径 —— 不烧 token。
- `report`:给定 `TeardownResult` 测 Markdown/JSON 渲染。
- 1 个可选的、需真实 key 的端到端冒烟测试(默认跳过)。

---

## 8. v1 明确不做(YAGNI)

以下全部留给 v2/v3,但接口边界已为它们预留:

- URL 抓取 / App Store 集成
- 截图多模态识别
- 向量检索(retriever 接口已预留)
- 知识库自动沉淀闭环
- HTTP API / 聊天界面
- Skill 封装、可复用 Workflow 抽象
- 多用户 / 持久化存储
