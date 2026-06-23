# 心理驱动型产品拆解 Agent · v2 设计文档

- 日期:2026-06-14
- 状态:已通过设计评审,待用户确认 spec
- 依赖:v1(已合并到 master)。本文档仅覆盖 **v2**。

---

## 1. 背景与目标

v1 已交付:种子知识库 + 5 步拆解流水线 + 可插拔 LLM provider + Markdown/JSON 报告(库为核心 + 薄 CLI)。但 v1 的拆解产物用完即弃,知识库是只读的随包 YAML。

v2 让工具拥有**情景记忆(episodic memory)**:每次拆解的结果落盘成"案例",并能用向量检索找到相似的历史案例。这是"知识库越用越厚"愿景的第一层地基。

### 记忆架构的三层(完整愿景,便于定位 v2)

| 层 | 沉淀什么 | 记忆类型 | 版本 |
|---|---|---|---|
| 1 | 每次的 `TeardownResult`(案例) | 情景记忆 | **v2(本文档)** |
| 2 | 提炼出的 look_for/原则/框架 | 语义记忆 | v3(后续) |
| 3 | 拆解策略 / 元认知反思 | 程序性记忆 | v4(后续) |

第 2、3 层都以"积累的案例"为原料,因此 v2(案例地基)是它们的前置。v2 只做第 1 层。

### v2 成功标准

1. 每次 `analyze` 跑完,自动把 `TeardownResult` 落盘为一个 `Case`(可 `--no-save` 关闭)。
2. 提供 `psyteardown similar` 命令,给定产品描述,检索并列出最相似的历史案例。
3. 相似度用可插拔的 `EmbeddingProvider`,默认本地模型(离线、不依赖外网)。
4. 案例库是单个 SQLite 文件;同一产品复跑按内容哈希 upsert,不重复膨胀。
5. 可选 `--use-memory` 开关:拆解前检索相似案例,把摘要作为参考注入 step3(机制映射),且不污染 step1(产品解析)。
6. 全部核心逻辑可脱离真实嵌入模型与网络测试(`FakeEmbeddingProvider`)。
7. v1 的 `run_teardown` 签名向后兼容(新增参数默认值 = v1 行为),v1 测试不受影响。

---

## 2. 关键决策(已确认)

| 维度 | 决策 |
|------|------|
| v2 范围 | 第 1 层情景记忆:案例库落盘 + 向量检索;第 2/3 层后置 v3/v4 |
| 相似度引擎 | 可插拔 `EmbeddingProvider`,默认本地 sentence-transformers 模型 |
| 存储 | SQLite 单文件(案例 JSON + 向量 blob + 元数据) |
| 案例用法 | 自动落盘 + 独立 `similar` 检索命令 + 可选 `--use-memory` 接入流水线 |
| 去重 | `case_id = sha256(embed_text)[:16]`,`INSERT OR REPLACE` upsert |
| 防污染 | 只注入 Top-K 摘要、标注"仅供参考"、step1 不注入 |

---

## 3. 架构与新模块

在 v1 之上新增 `embed/` 与 `memory/` 两个子系统,对 `pipeline`/`cli` 做最小侵入改动。

```
src/psyteardown/
├── kb/ pipeline/ llm/ report/ cli.py        # v1 既有
│     pipeline/orchestrator.py               #   仅新增可选参数 prior_cases
│     pipeline/steps.py                       #   map_features 接受可选参考摘要
│     cli.py                                  #   新增 similar 命令 + analyze 落盘/开关
├── embed/                                    # 新:嵌入 provider(对称于 llm/)
│   ├── __init__.py
│   ├── base.py          # EmbeddingProvider 抽象 + FakeEmbeddingProvider
│   └── local.py         # LocalEmbeddingProvider(默认,懒加载 sentence-transformers)
└── memory/                                   # 新:情景记忆子系统
    ├── __init__.py
    ├── models.py        # Case
    ├── embed_text.py    # TeardownResult/描述 → 规范化可嵌入文本
    ├── store.py         # CaseStore(SQLite 读写)
    └── retrieval.py     # search_similar(向量化 + 暴力余弦 → Top-K)
```

### 关键设计点

- `embed/` 完全对称 v1 的 `llm/`:抽象 + Fake(测试)+ 真实默认实现。`FakeEmbeddingProvider` 用确定性文本哈希生成向量 → 案例库与检索全链路离线可测,不碰 torch/网络。
- `LocalEmbeddingProvider` 懒加载模型(构造廉价,首次 `embed()` 才 import + 下载/加载)。
- `store` 只管持久化,`retrieval` 只管相似度计算,职责分离、各自可测。
- `embed_text()` 单点构造可嵌入文本;**存储与查询共用** → 向量可比。

### 数据流

- **落盘**:`run_teardown` → `TeardownResult` → CLI 构造 `Case` → `embed(embed_text(result))` → `store.save(case, vector)`。
- **检索**:查询文本 → `embed` → 与库中向量算余弦 → Top-K `Case`。
- **接入(`--use-memory`)**:拆解前检索相似案例 → 摘要注入 step3。

---

## 4. 数据模型与存储

### Case 模型(Pydantic)

```python
class Case(BaseModel):
    case_id: str            # sha256(embed_text)[:16];同产品复跑 → 同 id → upsert 去重
    product_name: str
    product_type: str
    one_liner: str
    frameworks_used: list[str]
    embed_text: str         # 规范化可嵌入文本(可追溯、可重算向量)
    result: TeardownResult  # v1 完整产物,原样嵌套
    created_at: str         # 调用方注入(沿用内核不调 datetime 的纪律)
```

### SQLite schema(单表)

```sql
CREATE TABLE IF NOT EXISTS cases (
    case_id      TEXT PRIMARY KEY,    -- upsert 键
    product_name TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    dim          INTEGER NOT NULL,    -- 向量维度,检索时校验一致
    embedding    BLOB NOT NULL,       -- float32 数组,numpy tobytes()
    case_json    TEXT NOT NULL        -- Case.model_dump_json()
);
```

### CaseStore 接口(只管持久化)

```python
class CaseStore:
    def __init__(self, db_path: Path): ...        # 建表 IF NOT EXISTS
    def save(self, case: Case, embedding: list[float]) -> None:  # INSERT OR REPLACE
    def all(self) -> list[tuple[Case, list[float]]]:  # 加载全部(检索时内存算余弦)
    def get(self, case_id: str) -> Case | None: ...
    def count(self) -> int: ...
```

### 关键设计点

- `case_id = sha256(embed_text)[:16]`:同产品同描述复跑 → 同 id → `INSERT OR REPLACE` 覆盖,天然防重复膨胀。
- 向量存 `float32` blob + `dim` 列;检索时 `dim` 与当前 provider 不一致 → 明确报错(换模型须重建库,不静默给错)。
- `case_json` 存完整 `TeardownResult`,案例库自包含、可离线复现报告。
- 库路径默认 `./.psyteardown/cases.db`(项目本地、可 .gitignore);CLI `--store` 可覆盖。

### 错误处理

- DB 损坏/无法打开 → 明确异常,不静默吞。
- 维度不匹配 → 自定义 `MemoryError`,提示"嵌入模型已变,请重建案例库"。
- 空库检索 → 返回 `[]`(不报错)。

---

## 5. 嵌入抽象、检索与流水线接入

### EmbeddingProvider 抽象(对称于 LLMProvider)

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...  # 批量,等长向量
    @property
    @abstractmethod
    def dim(self) -> int: ...


class FakeEmbeddingProvider(EmbeddingProvider):
    """测试用:确定性哈希 → 固定维向量,绝不触网/不加载 torch。
    把文本分词哈希到固定维 bucket,L2 归一化。
    相同文本→相同向量;相似文本→部分重叠。"""


class LocalEmbeddingProvider(EmbeddingProvider):
    """默认:懒加载 sentence-transformers 多语言模型
    (paraphrase-multilingual-MiniLM-L12-v2)。
    仅在首次 embed() 时 import + 加载模型 → 构造廉价、import 廉价。"""
```

### embed_text(单点构造可嵌入文本)

```python
def embed_text(result: TeardownResult) -> str:
    """把拆解结果规范化成一段可嵌入文本:
    产品类型 + 一句话 + 功能名 + 引用框架 id + 伦理标签。
    存储与查询共用此函数,保证向量可比。"""
```

`similar` 命令对纯描述检索时:先用 v1 的 `parse_product` 得到 `ProductProfile`,再走同一构造逻辑。实现阶段把"从 ProductProfile 构造文本"抽成内部函数 `_profile_embed_text(profile)`,供 `embed_text(result)` 和 `similar` 共用,签名在 plan 中固定。

### 检索(retrieval.py,纯计算)

```python
def search_similar(
    store: CaseStore,
    provider: EmbeddingProvider,
    query_text: str,
    top_k: int = 3,
) -> list[tuple[Case, float]]:
    """query_text 向量化,与库中全部向量算余弦,返回 Top-K (Case, score)。
    空库 → []。维度不匹配 → MemoryError。"""
```

暴力余弦(numpy),几千案例毫秒级,无需向量库。

### 流水线接入(`--use-memory` 可选开关)

`run_teardown` 签名向后兼容,新增可选参数:

```python
def run_teardown(provider, description, library, *, generated_at,
                 model_label=None, top_n=5,
                 prior_cases: list[Case] | None = None):  # 默认 None = v1 行为
```

- `prior_cases is None` → 完全 v1 行为(向后兼容)。
- 提供时:把相似案例的**精简摘要**(产品名 + 一句话 + 用过的框架 + 关键 mapping)拼进 **step3(机制映射)** 的 prompt 作为"历史参考"。

### 防"旧案例淹没新分析"

- 注入**摘要而非全文**,明确标注"仅供参考的历史相似案例,请独立判断当前产品,不要照搬"。
- 只注入 Top-K(默认 3)。
- **step1(产品解析)不注入** —— 产品画像必须忠于当前输入;只在 step3 注入参考。

### 落盘时机

CLI `analyze` 跑完 → 构造 `Case` → `embed` → `store.save`。默认开启;`--no-save` 可关。

### CLI 变更

```bash
psyteardown analyze --input p.txt [--use-memory] [--no-save] [--store PATH]
psyteardown similar --input p.txt [--top-k 3] [--store PATH]   # 列出相似历史案例
psyteardown memory stats [--store PATH]                         # 案例数等
```

`analyze`/`similar` 默认用 `LocalEmbeddingProvider`;测试经隐藏开关注入 `FakeEmbeddingProvider`,沿用 v1 `--provider fake` 模式。

---

## 6. 测试策略(TDD)

- `embed`:`FakeEmbeddingProvider` 确定性、`dim` 正确、相同文本同向量 — 纯单测。
- `store`:`tmp_path` 临时 db,测 save / upsert 去重 / get / count / 维度不匹配报错 — 真实 SQLite,不触网。
- `retrieval`:Fake 向量 + 临时库,测 Top-K 排序、空库返回 []、相似文本排前 — 离线。
- `embed_text`:同一 result 产出稳定文本;关键字段进入文本 — 纯单测。
- `pipeline`:`FakeProvider` + `prior_cases` 注入,断言参考摘要进了 step3 prompt、step1 prompt 未被污染、`prior_cases=None` 时与 v1 一致 — 离线。
- `cli`:`analyze` 落盘(+ `--no-save` 不落盘)、`similar` 检索、`--use-memory` — Fake 注入,不触网。
- 真实 `LocalEmbeddingProvider`:1 个可选冒烟测试,`PSYTEARDOWN_E2E=1` 才跑(同 v1 模式)。

---

## 7. v2 明确不做(YAGNI)

- 框架知识增长(第 2 层,语义记忆)
- 拆解策略 / 元认知反思(第 3 层,程序性记忆)
- 托管嵌入 API(Voyage/OpenAI 等)
- 专用向量数据库(暴力余弦已够个人/团队规模)
- 跨案例聚类、趋势分析、可视化
- 多用户 / 远程共享案例库

接口已为它们预留(`EmbeddingProvider` 可换托管实现;`CaseStore` 可换后端;`Case` 自包含便于后续提炼)。
