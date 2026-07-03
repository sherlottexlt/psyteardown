# 心理驱动型产品拆解 Agent · v3 设计文档

- 日期:2026-06-14
- 状态:已通过设计评审,待用户确认 spec
- 依赖:v1 + v2(已合并到 main)。本文档仅覆盖 **v3**。

---

## 1. 背景与目标

记忆架构三层中,v2 做了第 1 层(情景记忆:案例库 + 向量检索)。v3 做**第 2 层:语义记忆——框架知识增长**:从积累的案例里提炼出现有框架盖不住的**全新心理学框架**,经人工审批后回填知识库,让"知识库本身越用越厚"。

| 层 | 沉淀什么 | 记忆类型 | 版本 |
|---|---|---|---|
| 1 | 每次的 TeardownResult(案例) | 情景记忆 | v2(已完成) |
| 2 | 提炼出的**全新框架** | 语义记忆 | **v3(本文档)** |
| 3 | 拆解策略 / 元认知反思 | 程序性记忆 | v4(后续) |

### v3 成功标准

1. `psyteardown learn`:读案例库,提炼出现有框架未覆盖、且有足够案例支撑的**候选新框架**,写入候选区。
2. 候选经**人工审批**才进入知识库:`candidates list/show/approve/reject`;`approve` 后该框架被后续 `analyze` 使用。
3. **种子库永不被动**:`learn` 只写候选区;只有 `approve` 写"习得层";加载时种子 id 优先。
4. 三道质量闸:提炼时告知现有框架 + 要求 ≥min_support 案例支撑;嵌入相似度挡换皮重复;人工审批为最终闸。
5. 复用 v1/v2 抽象(`LLMProvider`/`EmbeddingProvider`/`Framework`/YAML 加载),全部核心逻辑离线可测(Fake)。
6. `load_frameworks` 向后兼容:不传 `learned_dir` 时行为与 v1/v2 完全一致。

---

## 2. 关键决策(已确认)

| 维度 | 决策 |
|------|------|
| 增长粒度 | **全新框架**(新 look_for / 新原则粒度不做,留后续) |
| 质量闸门 | 提案 → 人工审批 → 批准入库 |
| 存储 | YAML;候选 `./.psyteardown/candidates/*.yaml` → 习得 `./.psyteardown/learned/*.yaml` |
| 触发 | 按需 `learn` 命令(不自动) |
| 防重复 | 复用 `EmbeddingProvider` 算 summary 余弦;≥阈值或 id 冲突丢弃 |

---

## 3. 架构与流程

新增 `growth` 子系统 + 对 `kb/loader` 做最小扩展。复用 v1/v2 抽象,不重造轮子。

```
src/psyteardown/
├── kb/loader.py            # 改:load_frameworks 合并 种子 + learned/(种子优先,id 冲突跳过)
├── growth/                 # 新:语义记忆增长
│   ├── __init__.py
│   ├── models.py           # FrameworkCandidate + CandidateList
│   ├── proposer.py         # propose_frameworks(llm, cases, existing, ...) → 候选
│   ├── dedup.py            # filter_duplicates(cands, existing, embed, ...) 防换皮重复
│   └── store.py            # GrowthStore + GrowthError:候选/习得 YAML 读写
└── cli.py                  # 改:learn / candidates list|show|approve|reject
```

### 端到端流程(按需、人工把关)

```
psyteardown learn
   → 读案例库全部 Case 的机制摘要(mappings)
   → proposer:带「现有框架清单」问 LLM:哪些反复出现的机制现有框架盖不住?提候选
   → dedup:候选 summary 与现有框架 summary 算嵌入余弦,挡掉疑似重复
   → store:写 ./.psyteardown/candidates/<id>.yaml(含 rationale、source_case_ids)

psyteardown candidates list / show <id>      # 审阅
psyteardown candidates approve <id>          # 移到 ./.psyteardown/learned/<id>.yaml
psyteardown candidates reject <id>           # 删候选

→ 此后 analyze 加载 = 种子 + learned/(已批准);候选永不进入拆解
```

### 关键设计点

- **种子库永不被动**:`learn` 只写候选;`approve` 才写习得;`load_frameworks` 让种子 id 优先(习得不能覆盖种子)。
- **三道质量闸**:① proposer 被告知现有框架、要求引用 ≥min_support 案例;② dedup 嵌入挡重复;③ 人工 approve。
- 各子模块单一职责、可独立测试;LLM/嵌入走注入 provider → 离线可测。

---

## 4. 数据模型与存储

### FrameworkCandidate(候选 = 提议的 Framework + 出处元数据)

```python
class FrameworkCandidate(BaseModel):
    framework: Framework          # 复用 v1 模型
    rationale: str                # 为什么现有框架盖不住、这个模式是什么
    source_case_ids: list[str]    # 支撑此提案的案例(可追溯)
    created_at: str               # 调用方注入


class CandidateList(BaseModel):    # messages.parse 顶层需 object
    candidates: list[FrameworkCandidate]
```

### 存储布局(v2 已建的 `./.psyteardown/` 下,已 gitignore)

```
.psyteardown/
├── cases.db                 # v2 案例库
├── candidates/<id>.yaml     # learn 产出,待审;FrameworkCandidate 序列化
└── learned/<id>.yaml        # approve 后的习得框架;只存 Framework(与种子同构 → loader 直接读)
```

### GrowthStore 接口(职责:候选/习得的 YAML 读写)

```python
class GrowthError(Exception):
    """候选/习得读写错误(如 approve 不存在的 id)。"""


class GrowthStore:
    def __init__(self, root: Path):                # root 默认 ./.psyteardown
    def save_candidate(self, cand: FrameworkCandidate) -> None   # 写 candidates/<framework.id>.yaml
    def list_candidates(self) -> list[FrameworkCandidate]        # 读 candidates/*.yaml(按 id 排序)
    def get_candidate(self, fid: str) -> FrameworkCandidate | None
    def approve(self, fid: str) -> Path            # 写 learned/<id>.yaml(仅 framework 部分),删候选;返回路径
    def reject(self, fid: str) -> None             # 删 candidates/<id>.yaml
    def learned_dir(self) -> Path                  # 供 loader 合并
```

### loader 扩展

```python
def load_frameworks(directory=None, *, learned_dir=None) -> list[Framework]:
    # 1. 读种子(原行为不变)
    # 2. learned_dir 存在则读其中 *.yaml;id 与种子冲突 → 跳过 + 警告(种子优先)
    # 3. 合并、按 id 排序返回
```

### 关键设计点

- `learned/<id>.yaml` **只存 Framework**(不含候选元数据)→ 与种子完全同构,loader 零特判;出处/理由在候选阶段已审过,批准即定稿。
- `approve` 是"移动":先写 learned、后删候选。
- 向后兼容:`load_frameworks()` 不传 `learned_dir` 时与 v1/v2 一致;CLI 默认传 `learned_dir=<root>/learned`。

### 错误处理

- `approve`/`reject` 不存在的 id → `GrowthError`。
- 候选 id 与现有(种子 + 习得)冲突 → `learn` 阶段丢弃并记录(不写入)。
- learned/ 里坏 YAML → 沿用 v1 的 `KBLoadError`(同一套校验)。

---

## 5. 提炼机制、防重复、CLI

### proposer.py(复用 LLMProvider,结构化输出)

```python
def propose_frameworks(
    provider: LLMProvider,
    cases: list[Case],
    existing: list[Framework],
    *, min_support: int = 3, max_candidates: int = 5,
) -> list[FrameworkCandidate]:
    """把案例机制摘要 + 现有框架清单喂给 LLM,要求提出现有框架盖不住、
    且至少 min_support 个案例支撑的新框架。空案例库 → []。"""
```

- prompt 明确给出**现有框架 id/name/summary 全表**,要求 LLM 只提"不属于任何现有框架"的模式,并引用 `source_case_ids`;`source_case_ids` 少于 `min_support` 的候选丢弃。
- 案例机制摘要 = 每个 Case 的 `mappings`(feature → framework·principle → evidence)压缩,控制 token。
- 至多 `max_candidates` 个。

### dedup.py(复用 EmbeddingProvider)

```python
def filter_duplicates(
    candidates: list[FrameworkCandidate],
    existing: list[Framework],
    embed: EmbeddingProvider,
    *, threshold: float = 0.85,
) -> list[FrameworkCandidate]:
    """对每个候选,用其 framework.summary 与现有框架 summary 算余弦;
    ≥threshold 视为换皮重复,丢弃;framework.id 与现有冲突也丢弃。"""
```

- 同一个 `EmbeddingProvider` 既做 v2 案例检索,又挡框架重复。
- 嵌入不可用(离线)时降级为**只按 id/name 去重**并警告(不阻断 `learn`)。

### CLI 变更

```bash
psyteardown learn [--store PATH] [--min-support 3]     # 生成候选(需 LLM;嵌入可选)
psyteardown candidates list [--store PATH]             # 列候选
psyteardown candidates show <id> [--store PATH]        # 看候选详情(理由/出处/框架)
psyteardown candidates approve <id> [--store PATH]     # → learned/
psyteardown candidates reject <id> [--store PATH]      # 删候选
```

- `learn` 用 `--provider`(LLM)+ `--embed-provider`(去重);测试注入 fake,沿用 v1/v2 隐藏开关模式。
- `analyze`/`kb list` 加载知识库时默认合并 `learned/`(已批准习得框架自动生效)。
- 嵌入不可用时 `learn` 降级(见 dedup),核心提炼仍产出候选。

---

## 6. 测试策略(TDD,全部离线)

- `growth/models`:FrameworkCandidate 校验 / JSON 往返 — 纯单测。
- `proposer`:`FakeProvider` 注入固定候选;断言现有框架清单进 prompt、min_support 过滤、空库→[] — 离线。
- `dedup`:`FakeEmbeddingProvider`;高相似丢弃、id 冲突丢弃、嵌入不可用降级 — 离线。
- `store`:`tmp_path` 建 candidates/learned;save/list/get/approve(移动)/reject/不存在报错 — 真实文件。
- `loader` 扩展:tmp 种子 + learned 合并、种子 id 优先、不传 learned_dir 与 v1 一致 — 离线。
- `cli`:`learn`(Fake LLM + Fake 嵌入)、candidates 全流程、approve 后 analyze 能加载到新框架 — 离线。
- 不新增可选 e2e(v3 无新外部依赖;LLM/嵌入沿用 v1/v2 的 e2e)。

---

## 7. v3 明确不做(YAGNI)

- 自动触发(仅按需 `learn`)
- 新 look_for / 新原则粒度(本版只做整框架)
- 拆解策略 / 元认知反思(第 3 层,v4)
- 候选自动入库(必须人工审批)
- 跨案例聚类 / 趋势可视化
- 习得框架的版本管理 / 回滚(用 git 管理 `.psyteardown/learned/` 即可,若纳入版本控制)

接口已为后续预留(`FrameworkCandidate` 带出处便于 v4 追溯;`GrowthStore` 可扩展 look_for/principle 粒度的候选)。
