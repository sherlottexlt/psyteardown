# v2 情景记忆 + 向量检索 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 v1 加上情景记忆——每次拆解落盘为案例(SQLite),用可插拔嵌入 + 向量检索找相似历史案例,并可选注入流水线。

**Architecture:** 新增 `embed/`(对称 v1 的 `llm/`:抽象 + Fake + 本地默认实现)与 `memory/`(Case 模型、SQLite CaseStore、向量检索)。pipeline 保持对 memory 零依赖:`run_teardown` 接收预构造的 `prior_summary: str`,由 CLI 用 `memory.summarize_cases` 生成。全部核心逻辑用 `FakeEmbeddingProvider` 离线可测。

**Tech Stack:** 沿用 v1(Python 3.11+、Pydantic v2、Typer、anthropic、pytest)+ numpy(向量运算/blob)+ sentence-transformers(可选 extra,默认嵌入实现)。

> **对 spec 的两处落地精化(已在 plan 中固定):**
> 1. **嵌入对象是原始产品描述**,不是规范化 profile 文本 → 删除 `memory/embed_text.py`;`case_id = sha256(description)[:16]`;`similar` 无需 LLM 调用;存/查文本同源,天然可比。
> 2. **pipeline 不依赖 memory**:`run_teardown(..., prior_summary: str | None)` 收预构造字符串;CLI 用 `memory.summarize_cases(cases)` 生成。异常类名用 `MemoryStoreError`(避开 Python 内置 `MemoryError`)。

---

## 文件结构

```
pyproject.toml                              # 改:加 numpy 依赖 + [embed] 可选 extra
.gitignore                                  # 改:加 .psyteardown/
src/psyteardown/
├── embed/
│   ├── __init__.py                         # 新(空)
│   ├── base.py                             # 新:EmbeddingProvider + FakeEmbeddingProvider
│   └── local.py                            # 新:LocalEmbeddingProvider(懒加载)
├── memory/
│   ├── __init__.py                         # 新(空)
│   ├── models.py                           # 新:Case + case_id_for()
│   ├── store.py                            # 新:CaseStore + MemoryStoreError
│   └── retrieval.py                        # 新:search_similar + summarize_cases
├── pipeline/
│   ├── steps.py                            # 改:map_features 加 prior_summary 参数
│   └── orchestrator.py                     # 改:run_teardown 加 prior_summary 参数
└── cli.py                                  # 改:analyze 加开关+落盘;新增 similar / memory stats
tests/
├── embed/test_fake_embedding.py            # 新
├── memory/test_models.py                   # 新
├── memory/test_store.py                    # 新
├── memory/test_retrieval.py                # 新
├── pipeline/test_steps_memory.py           # 新(prior_summary 注入)
├── pipeline/test_orchestrator_memory.py    # 新(step1 不污染)
├── test_cli_memory.py                      # 新(analyze 落盘 / similar / stats)
└── test_smoke_embed_e2e.py                 # 新(可选,默认 skip)
```

---

## Task 1: 依赖与 .gitignore

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: 加 numpy 到 dependencies,加 [embed] 可选 extra**

把 `pyproject.toml` 的 `[project]` dependencies 改为(在原 4 个基础上加 numpy):
```toml
dependencies = [
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "typer>=0.12",
    "anthropic>=0.69",
    "numpy>=1.26",
]
```
并把 optional-dependencies 改为:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
embed = ["sentence-transformers>=2.2"]
```

- [ ] **Step 2: .gitignore 加案例库目录**

向 `.gitignore` 追加一行:
```
.psyteardown/
```

- [ ] **Step 3: 安装新依赖并验证**

Run: `pip install -e ".[dev]" && python -c "import numpy; print('numpy', numpy.__version__)"`
Expected: 打印 numpy 版本,无错误。

- [ ] **Step 4: 确认 v1 全绿(未回归)**

Run: `pytest -q`
Expected: `39 passed, 1 skipped`

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml .gitignore
git commit -m "chore: add numpy dep and sentence-transformers extra for v2"
```

---

## Task 2: EmbeddingProvider 抽象 + FakeEmbeddingProvider

**Files:**
- Create: `src/psyteardown/embed/__init__.py` (空)
- Create: `src/psyteardown/embed/base.py`
- Test: `tests/embed/test_fake_embedding.py`

- [ ] **Step 1: 写失败测试**

`tests/embed/__init__.py`: 空文件。
`tests/embed/test_fake_embedding.py`:
```python
import math

from psyteardown.embed.base import EmbeddingProvider, FakeEmbeddingProvider


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def test_is_embedding_provider():
    assert isinstance(FakeEmbeddingProvider(), EmbeddingProvider)


def test_dim_matches_vector_length():
    p = FakeEmbeddingProvider(dim=32)
    assert p.dim == 32
    [vec] = p.embed(["你好"])
    assert len(vec) == 32


def test_same_text_same_vector():
    p = FakeEmbeddingProvider()
    [a] = p.embed(["每日签到App"])
    [b] = p.embed(["每日签到App"])
    assert a == b


def test_identical_text_cosine_is_one():
    p = FakeEmbeddingProvider()
    [a] = p.embed(["每日签到App"])
    assert _cos(a, a) == 1.0 or abs(_cos(a, a) - 1.0) < 1e-6


def test_batch_returns_one_vector_per_text():
    p = FakeEmbeddingProvider()
    vecs = p.embed(["a", "bb", "ccc"])
    assert len(vecs) == 3
    assert all(len(v) == p.dim for v in vecs)


def test_overlapping_text_more_similar_than_disjoint():
    p = FakeEmbeddingProvider()
    [base] = p.embed(["签到打卡习惯养成推送"])
    [near] = p.embed(["签到打卡习惯养成"])
    [far] = p.embed(["金融理财股票基金"])
    assert _cos(base, near) > _cos(base, far)
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/embed/test_fake_embedding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.embed'`

- [ ] **Step 3: 实现抽象 + Fake**

`src/psyteardown/embed/__init__.py`: 空文件。
`src/psyteardown/embed/base.py`:
```python
"""嵌入 provider 抽象。对称于 llm/:抽象 + Fake(测试)+ 真实默认实现。"""

import hashlib
from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量把文本转成等长向量。"""

    @property
    @abstractmethod
    def dim(self) -> int:
        """向量维度。"""


class FakeEmbeddingProvider(EmbeddingProvider):
    """测试用:确定性字符哈希 → 固定维向量,L2 归一化。绝不触网/不加载 torch。"""

    def __init__(self, dim: int = 64):
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            v = np.zeros(self._dim, dtype=np.float32)
            for ch in text:
                h = int(hashlib.sha256(ch.encode("utf-8")).hexdigest(), 16)
                v[h % self._dim] += 1.0
            norm = float(np.linalg.norm(v))
            if norm > 0:
                v = v / norm
            out.append(v.astype(float).tolist())
        return out
```

- [ ] **Step 4: 运行,确认 PASS(6 passed)**

Run: `pytest tests/embed/test_fake_embedding.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/embed/__init__.py src/psyteardown/embed/base.py tests/embed/__init__.py tests/embed/test_fake_embedding.py
git commit -m "feat: add EmbeddingProvider abstraction and FakeEmbeddingProvider"
```

---

## Task 3: LocalEmbeddingProvider(默认实现)

**Files:**
- Create: `src/psyteardown/embed/local.py`

> 说明:不写单测(避免下载模型/触网)。验证为 import-only。正确性由 Task 9 可选冒烟测试覆盖。

- [ ] **Step 1: 实现 LocalEmbeddingProvider**

`src/psyteardown/embed/local.py`:
```python
"""默认嵌入实现:本地 sentence-transformers 多语言模型,懒加载。"""

from psyteardown.embed.base import EmbeddingProvider

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class LocalEmbeddingProvider(EmbeddingProvider):
    """构造廉价;仅在首次 embed()/dim 访问时 import 并加载模型。"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self._model_name = model_name
        self._model = None
        self._dim: int | None = None

    def _ensure(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        self._ensure()
        assert self._dim is not None
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure()
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [[float(x) for x in v] for v in vecs]
```

- [ ] **Step 2: 验证可导入(不触发模型加载)**

Run: `python -c "from psyteardown.embed.local import LocalEmbeddingProvider, DEFAULT_MODEL; p=LocalEmbeddingProvider(); print('import OK', DEFAULT_MODEL)"`
Expected: 打印 `import OK sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`,无错误(构造不加载模型)。

- [ ] **Step 3: 提交**

```bash
git add src/psyteardown/embed/local.py
git commit -m "feat: add LocalEmbeddingProvider (lazy sentence-transformers)"
```

---

## Task 4: Case 模型 + case_id_for

**Files:**
- Create: `src/psyteardown/memory/__init__.py` (空)
- Create: `src/psyteardown/memory/models.py`
- Test: `tests/memory/test_models.py`

- [ ] **Step 1: 写失败测试**

`tests/memory/__init__.py`: 空文件。
`tests/memory/test_models.py`:
```python
from psyteardown.memory.models import Case, case_id_for
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result():
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="App",
                               one_liner="每日签到App", features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[],
        assessment=ExperienceAssessment(),
        executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="2026-06-14"),
    )


def test_case_id_is_deterministic_16_hex():
    a = case_id_for("每日签到App,有推送提醒")
    b = case_id_for("每日签到App,有推送提醒")
    assert a == b
    assert len(a) == 16
    assert case_id_for("别的产品") != a


def test_from_result_builds_case():
    case = Case.from_result(_result(), description="每日签到App描述", created_at="2026-06-14")
    assert case.case_id == case_id_for("每日签到App描述")
    assert case.product_name == "Demo"
    assert case.product_type == "App"
    assert case.one_liner == "每日签到App"
    assert case.frameworks_used == ["hook-model"]
    assert case.description == "每日签到App描述"
    assert case.result.executive_summary == "s"


def test_case_json_roundtrip():
    case = Case.from_result(_result(), description="d", created_at="t")
    again = Case.model_validate_json(case.model_dump_json())
    assert again.case_id == case.case_id
    assert again.result.product.name == "Demo"
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/memory/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.memory'`

- [ ] **Step 3: 实现 Case + case_id_for**

`src/psyteardown/memory/__init__.py`: 空文件。
`src/psyteardown/memory/models.py`:
```python
"""情景记忆的案例模型。"""

import hashlib

from pydantic import BaseModel, Field

from psyteardown.pipeline.schemas import TeardownResult


def case_id_for(description: str) -> str:
    """案例 id = 原始描述的 sha256 前 16 位(同描述复跑 → 同 id → upsert 去重)。"""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:16]


class Case(BaseModel):
    case_id: str
    product_name: str
    product_type: str
    one_liner: str
    frameworks_used: list[str] = Field(default_factory=list)
    description: str           # 被嵌入的原始产品描述(可追溯、可重算向量)
    result: TeardownResult     # v1 完整产物,原样嵌套
    created_at: str            # 调用方注入

    @classmethod
    def from_result(
        cls, result: TeardownResult, description: str, created_at: str
    ) -> "Case":
        return cls(
            case_id=case_id_for(description),
            product_name=result.product.name,
            product_type=result.product.product_type,
            one_liner=result.product.one_liner,
            frameworks_used=result.frameworks_used,
            description=description,
            result=result,
            created_at=created_at,
        )
```

- [ ] **Step 4: 运行,确认 PASS(3 passed)**

Run: `pytest tests/memory/test_models.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/memory/__init__.py src/psyteardown/memory/models.py tests/memory/__init__.py tests/memory/test_models.py
git commit -m "feat: add Case model and case_id_for"
```

---

## Task 5: CaseStore(SQLite)

**Files:**
- Create: `src/psyteardown/memory/store.py`
- Test: `tests/memory/test_store.py`

- [ ] **Step 1: 写失败测试**

`tests/memory/test_store.py`:
```python
import pytest

from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result(name="Demo"):
    return TeardownResult(
        product=ProductProfile(name=name, product_type="App",
                               one_liner="x", features=[], touchpoints=[]),
        frameworks_used=["hook-model"], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def _case(desc, name="Demo"):
    return Case.from_result(_result(name), description=desc, created_at="t")


def test_save_and_count(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    assert store.count() == 0
    store.save(_case("产品A"), [0.1, 0.2, 0.3])
    assert store.count() == 1


def test_get_returns_case(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    case = _case("产品A")
    store.save(case, [0.1, 0.2, 0.3])
    got = store.get(case.case_id)
    assert got is not None
    assert got.product_name == "Demo"
    assert got.description == "产品A"


def test_get_missing_returns_none(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    assert store.get("deadbeefdeadbeef") is None


def test_upsert_same_description_no_duplicate(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    store.save(_case("产品A", name="旧名"), [0.1, 0.2, 0.3])
    store.save(_case("产品A", name="新名"), [0.4, 0.5, 0.6])  # 同描述 → 同 id → 覆盖
    assert store.count() == 1
    assert store.get(_case("产品A").case_id).product_name == "新名"


def test_all_roundtrips_case_and_vector(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    store.save(_case("产品A"), [0.1, 0.2, 0.3])
    rows = store.all()
    assert len(rows) == 1
    case, vec = rows[0]
    assert case.description == "产品A"
    assert len(vec) == 3
    assert abs(vec[0] - 0.1) < 1e-6


def test_creates_parent_dir(tmp_path):
    store = CaseStore(tmp_path / "nested" / "dir" / "cases.db")
    store.save(_case("产品A"), [0.1])
    assert (tmp_path / "nested" / "dir" / "cases.db").exists()
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/memory/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.memory.store'`

- [ ] **Step 3: 实现 CaseStore + MemoryStoreError**

`src/psyteardown/memory/store.py`:
```python
"""案例库:单文件 SQLite,存案例 JSON + float32 向量 blob + 元数据。"""

import sqlite3
from pathlib import Path

import numpy as np

from psyteardown.memory.models import Case


class MemoryStoreError(Exception):
    """案例库读写或一致性错误。"""  # 注意:不用内置名 MemoryError


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id      TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    dim          INTEGER NOT NULL,
    embedding    BLOB NOT NULL,
    case_json    TEXT NOT NULL
)
"""


class CaseStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save(self, case: Case, embedding: list[float]) -> None:
        arr = np.asarray(embedding, dtype=np.float32)
        self._conn.execute(
            "INSERT OR REPLACE INTO cases "
            "(case_id, product_name, created_at, dim, embedding, case_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (case.case_id, case.product_name, case.created_at,
             int(arr.shape[0]), arr.tobytes(), case.model_dump_json()),
        )
        self._conn.commit()

    def all(self) -> list[tuple[Case, list[float]]]:
        rows = self._conn.execute(
            "SELECT case_json, embedding FROM cases"
        ).fetchall()
        out: list[tuple[Case, list[float]]] = []
        for case_json, blob in rows:
            case = Case.model_validate_json(case_json)
            vec = np.frombuffer(blob, dtype=np.float32).tolist()
            out.append((case, vec))
        return out

    def get(self, case_id: str) -> Case | None:
        row = self._conn.execute(
            "SELECT case_json FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0])
```

- [ ] **Step 4: 运行,确认 PASS(6 passed)**

Run: `pytest tests/memory/test_store.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/memory/store.py tests/memory/test_store.py
git commit -m "feat: add CaseStore (SQLite, upsert by case_id)"
```

---

## Task 6: 检索 search_similar + summarize_cases

**Files:**
- Create: `src/psyteardown/memory/retrieval.py`
- Test: `tests/memory/test_retrieval.py`

- [ ] **Step 1: 写失败测试**

`tests/memory/test_retrieval.py`:
```python
import pytest

from psyteardown.embed.base import FakeEmbeddingProvider
from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore, MemoryStoreError
from psyteardown.memory.retrieval import search_similar, summarize_cases
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result(name):
    return TeardownResult(
        product=ProductProfile(name=name, product_type="App",
                               one_liner=f"{name}的一句话", features=[], touchpoints=[]),
        frameworks_used=["hook-model"], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def _save(store, emb, desc, name):
    case = Case.from_result(_result(name), description=desc, created_at="t")
    store.save(case, emb.embed([desc])[0])
    return case


def test_empty_store_returns_empty(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    emb = FakeEmbeddingProvider()
    assert search_similar(store, emb, "随便查", top_k=3) == []


def test_most_similar_ranked_first(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    emb = FakeEmbeddingProvider()
    _save(store, emb, "签到打卡习惯养成推送提醒", "签到App")
    _save(store, emb, "股票基金理财投资收益", "理财App")
    hits = search_similar(store, emb, "签到打卡习惯养成", top_k=2)
    assert hits[0][0].product_name == "签到App"
    assert hits[0][1] >= hits[1][1]


def test_respects_top_k(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    emb = FakeEmbeddingProvider()
    for i in range(5):
        _save(store, emb, f"产品描述{i}", f"产品{i}")
    assert len(search_similar(store, emb, "产品描述0", top_k=2)) == 2


def test_dim_mismatch_raises(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    _save(store, FakeEmbeddingProvider(dim=64), "产品A", "A")
    with pytest.raises(MemoryStoreError):
        search_similar(store, FakeEmbeddingProvider(dim=32), "产品A", top_k=1)


def test_summarize_cases_includes_name_and_frameworks():
    case = Case.from_result(_result("签到App"), description="d", created_at="t")
    text = summarize_cases([case])
    assert "签到App" in text
    assert "hook-model" in text


def test_summarize_empty_returns_empty_string():
    assert summarize_cases([]) == ""
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/memory/test_retrieval.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.memory.retrieval'`

- [ ] **Step 3: 实现检索 + 摘要**

`src/psyteardown/memory/retrieval.py`:
```python
"""向量检索(暴力余弦)+ 案例摘要(供流水线参考注入)。"""

import numpy as np

from psyteardown.embed.base import EmbeddingProvider
from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore, MemoryStoreError


def search_similar(
    store: CaseStore,
    provider: EmbeddingProvider,
    query_text: str,
    top_k: int = 3,
) -> list[tuple[Case, float]]:
    """query_text 向量化,与库中全部向量算余弦,返回 Top-K (Case, score)。
    空库 → [];维度不匹配 → MemoryStoreError。"""
    rows = store.all()
    if not rows:
        return []
    q = np.asarray(provider.embed([query_text])[0], dtype=np.float32)
    qn = float(np.linalg.norm(q))
    scored: list[tuple[Case, float]] = []
    for case, vec in rows:
        v = np.asarray(vec, dtype=np.float32)
        if v.shape != q.shape:
            raise MemoryStoreError(
                f"向量维度不匹配:库中 {v.shape[0]} vs 当前 provider {q.shape[0]}。"
                "换了嵌入模型须重建案例库。"
            )
        vn = float(np.linalg.norm(v))
        score = float(q @ v / (qn * vn)) if qn and vn else 0.0
        scored.append((case, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def summarize_cases(cases: list[Case]) -> str:
    """把相似案例压成精简参考摘要(产品名 + 一句话 + 用过的框架)。空 → ''。"""
    lines: list[str] = []
    for c in cases:
        fw = ", ".join(c.frameworks_used) or "—"
        lines.append(f"- {c.product_name}({c.one_liner}):用过框架 {fw}")
    return "\n".join(lines)
```

- [ ] **Step 4: 运行,确认 PASS(6 passed)**

Run: `pytest tests/memory/test_retrieval.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/memory/retrieval.py tests/memory/test_retrieval.py
git commit -m "feat: add vector retrieval and case summarization"
```

---

## Task 7: 流水线参考注入(prior_summary)

**Files:**
- Modify: `src/psyteardown/pipeline/steps.py`
- Modify: `src/psyteardown/pipeline/orchestrator.py`
- Test: `tests/pipeline/test_steps_memory.py`
- Test: `tests/pipeline/test_orchestrator_memory.py`

> 说明:`map_features` 与 `run_teardown` 各加一个可选 `prior_summary: str | None = None`,默认 None 时行为与 v1 完全一致。参考摘要只注入 step3(map_features),step1(parse_product)不注入。

- [ ] **Step 1: 写失败测试(steps)**

`tests/pipeline/test_steps_memory.py`:
```python
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList,
)


def _fw():
    return Framework(
        id="habit", name="上瘾模型", category="habit", summary="s", tags=["签到"],
        principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
        references=["r"],
    )


def _profile():
    return ProductProfile(
        name="Demo", product_type="App", one_liner="x",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=[],
    )


def _mapping():
    return Mapping(feature="签到", framework_id="habit", principle_id="trigger",
                   rationale="r", evidence="e", confidence=0.9)


def test_prior_summary_injected_into_step3_prompt():
    provider = FakeProvider(structured_responses=[MappingList(mappings=[_mapping()])])
    steps.map_features(provider, _profile(), [_fw()],
                       prior_summary="- 旧产品X(一句话):用过框架 hook-model")
    prompt = provider.calls[0]["prompt"]
    assert "旧产品X" in prompt
    assert "仅供参考" in prompt  # 防照搬提示


def test_no_prior_summary_means_no_reference_block():
    provider = FakeProvider(structured_responses=[MappingList(mappings=[_mapping()])])
    steps.map_features(provider, _profile(), [_fw()])  # 默认 None
    assert "仅供参考" not in provider.calls[0]["prompt"]
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/pipeline/test_steps_memory.py -v`
Expected: FAIL — `TypeError: map_features() got an unexpected keyword argument 'prior_summary'`

- [ ] **Step 3: 改 `map_features` 支持 prior_summary**

把 `src/psyteardown/pipeline/steps.py` 的 `map_features` 整个函数替换为:
```python
def map_features(
    provider: LLMProvider,
    profile: ProductProfile,
    frameworks: list[Framework],
    prior_summary: str | None = None,
) -> list[Mapping]:
    """Step 3:逐功能/触点映射到框架原则。单项失败标 error 并继续。
    prior_summary 提供时,作为"仅供参考的历史相似案例"注入(不污染产品画像)。"""
    brief = _frameworks_brief(frameworks)
    valid_ids = ", ".join(fw.id for fw in frameworks)
    ref_block = ""
    if prior_summary:
        ref_block = (
            "\n以下是仅供参考的历史相似案例,请独立判断当前产品,不要照搬:\n"
            f"{prior_summary}\n"
        )
    targets = [f.name for f in profile.features] + profile.touchpoints
    mappings: list[Mapping] = []
    for target in targets:
        prompt = (
            f"可用心理学框架:\n{brief}\n"
            f"{ref_block}\n"
            f"产品「{profile.name}」的功能/触点:「{target}」。\n"
            "请判断它用到了哪个框架的哪条原则、在产品中的具体体现、为何有效,"
            "并给出 0-1 的置信度。framework_id 必须来自这些 id: "
            f"{valid_ids}。若适用多条,返回最贴切的若干条 mapping。"
        )
        try:
            result = provider.structured_complete(prompt, MappingList, system=_SYSTEM)
            mappings.extend(result.mappings)
        except LLMError as e:
            mappings.append(
                Mapping(
                    feature=target, framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error=str(e),
                )
            )
    return mappings
```

- [ ] **Step 4: 运行,确认 steps 测试 PASS(2 passed)**

Run: `pytest tests/pipeline/test_steps_memory.py -v`

- [ ] **Step 5: 写失败测试(orchestrator)**

`tests/pipeline/test_orchestrator_memory.py`:
```python
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _library():
    return [Framework(
        id="habit", name="上瘾模型", category="habit", summary="s", tags=["签到"],
        principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
        references=["r"],
    )]


def _queue():
    profile = ProductProfile(
        name="Demo", product_type="App", one_liner="每日签到App",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=[],
    )
    mapping = Mapping(feature="签到", framework_id="habit", principle_id="trigger",
                      rationale="r", evidence="e", confidence=0.9)
    return [
        profile,                                   # step1
        MappingList(mappings=[mapping]),           # step3(只有1个 feature,无 touchpoint)
        ExperienceAssessment(),                    # step4
        Synthesis(executive_summary="总结"),       # step5
    ]


def test_prior_summary_reaches_step3_not_step1():
    provider = FakeProvider(structured_responses=_queue())
    run_teardown(provider, "每日签到App描述", library=_library(),
                 generated_at="2026-06-14", prior_summary="- 旧产品X(y):用过框架 hook-model")
    step1_prompt = provider.calls[0]["prompt"]   # parse_product
    step3_prompt = provider.calls[1]["prompt"]   # map_features
    assert "旧产品X" not in step1_prompt          # step1 不被污染
    assert "旧产品X" in step3_prompt              # step3 收到参考


def test_default_no_prior_summary_matches_v1():
    provider = FakeProvider(structured_responses=_queue())
    result = run_teardown(provider, "desc", library=_library(), generated_at="t")
    assert result.executive_summary == "总结"
    assert "仅供参考" not in provider.calls[1]["prompt"]
```

- [ ] **Step 6: 运行,确认 FAIL**

Run: `pytest tests/pipeline/test_orchestrator_memory.py -v`
Expected: FAIL — `TypeError: run_teardown() got an unexpected keyword argument 'prior_summary'`

- [ ] **Step 7: 改 `run_teardown` 支持 prior_summary**

在 `src/psyteardown/pipeline/orchestrator.py` 中:把 `run_teardown` 签名与 step3 调用改为:
```python
def run_teardown(
    provider: LLMProvider,
    description: str,
    library: list[Framework],
    *,
    generated_at: str,
    model_label: str | None = None,
    top_n: int = 5,
    prior_summary: str | None = None,
) -> TeardownResult:
    """跑完整流水线。generated_at 由调用方传入(脚本环境禁用 datetime.now)。
    prior_summary 提供时作为历史参考注入 step3(map_features)。"""
    profile = steps.parse_product(provider, description)
    frameworks = steps.retrieve(profile, library, top_n=top_n)
    mappings = steps.map_features(provider, profile, frameworks, prior_summary=prior_summary)
    assessment = steps.assess_experience(provider, profile, mappings)
    summary = steps.synthesize(provider, profile, mappings, assessment)
```
(其余 `return TeardownResult(...)` 与 `_provider_label` 不变。)

- [ ] **Step 8: 运行,确认 orchestrator 测试 PASS + 全量回归**

Run: `pytest tests/pipeline/ -q`
Expected: 全部通过(含 v1 既有 pipeline 测试,因默认值向后兼容)。

Run: `pytest -q`
Expected: 之前的都在 + 新增,`1 skipped`(v1 e2e),无失败。

- [ ] **Step 9: 提交**

```bash
git add src/psyteardown/pipeline/steps.py src/psyteardown/pipeline/orchestrator.py tests/pipeline/test_steps_memory.py tests/pipeline/test_orchestrator_memory.py
git commit -m "feat: inject prior-case summary into step3 (memory-aware teardown)"
```

---

## Task 8: CLI —— analyze 落盘/开关 + similar + memory stats

**Files:**
- Modify: `src/psyteardown/cli.py`
- Test: `tests/test_cli_memory.py`

> 说明:`analyze` 新增 `--store/--use-memory/--no-save/--embed-provider`(后者隐藏,测试注入 fake);默认落盘。新增 `similar` 命令与 `memory stats` 子命令。沿用 v1 `--provider fake` 模式,测试不触网/不加载 torch。

- [ ] **Step 1: 写失败测试**

`tests/test_cli_memory.py`:
```python
from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()
FAKE = ["--provider", "fake", "--embed-provider", "fake"]


def _write(tmp_path, text="一个每日签到App,有推送提醒。"):
    p = tmp_path / "product.txt"
    p.write_text(text, encoding="utf-8")
    return p


def test_analyze_saves_case_to_store(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--out", str(tmp_path / "r.md"), *FAKE])
    assert r.exit_code == 0, r.stdout
    stats = runner.invoke(app, ["memory", "stats", "--store", str(db)])
    assert "1" in stats.stdout


def test_no_save_skips_store(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--no-save", "--out", str(tmp_path / "r.md"), *FAKE])
    assert r.exit_code == 0, r.stdout
    stats = runner.invoke(app, ["memory", "stats", "--store", str(db)])
    assert "0" in stats.stdout


def test_similar_finds_saved_case(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                        "--out", str(tmp_path / "r.md"), *FAKE])
    r = runner.invoke(app, ["similar", "--input", str(src), "--store", str(db),
                            "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert "样例产品" in r.stdout  # fake LLM provider 产出的产品名


def test_similar_empty_store_message(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "empty.db"
    r = runner.invoke(app, ["similar", "--input", str(src), "--store", str(db),
                            "--embed-provider", "fake"])
    assert r.exit_code == 0
    assert "空" in r.stdout


def test_use_memory_runs_without_error(tmp_path):
    src = _write(tmp_path)
    db = tmp_path / "cases.db"
    # 先存一个案例,再带 --use-memory 跑一次
    runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                        "--out", str(tmp_path / "r1.md"), *FAKE])
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--use-memory", "--out", str(tmp_path / "r2.md"), *FAKE])
    assert r.exit_code == 0, r.stdout
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/test_cli_memory.py -v`
Expected: FAIL — analyze 无 `--store` 选项 / 无 `similar` / 无 `memory` 命令(报 usage error 或 exit≠0)。

- [ ] **Step 3: 改 CLI**

把 `src/psyteardown/cli.py` 整体替换为下面内容(在 v1 基础上扩展;保留 v1 的 `analyze` 行为,新增选项默认值不改变旧行为;并新增 `_build_embed_provider`、`similar`、`memory stats`):
```python
"""薄 CLI:读输入 → 调内核 → 写输出。零业务逻辑。"""

from datetime import datetime
from pathlib import Path

import typer

from psyteardown.kb.loader import load_frameworks
from psyteardown.llm.base import FakeProvider, LLMProvider
from psyteardown.embed.base import EmbeddingProvider, FakeEmbeddingProvider
from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore
from psyteardown.memory.retrieval import search_similar, summarize_cases
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.report.render import render_json, render_markdown
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, Synthesis,
)

app = typer.Typer(help="心理驱动型产品拆解 Agent(v2)")
kb_app = typer.Typer(help="知识库操作")
memory_app = typer.Typer(help="案例库操作")
app.add_typer(kb_app, name="kb")
app.add_typer(memory_app, name="memory")

DEFAULT_STORE = Path(".psyteardown/cases.db")


def _build_provider(name: str) -> LLMProvider:
    if name == "fake":
        return FakeProvider(structured_responses=[
            ProductProfile(name="样例产品", product_type="App",
                           one_liner="自动生成的占位画像", features=[], touchpoints=[]),
            ExperienceAssessment(),
            Synthesis(executive_summary="(fake provider 占位摘要)"),
        ])
    from psyteardown.llm.claude import ClaudeProvider

    return ClaudeProvider()


def _build_embed_provider(name: str) -> EmbeddingProvider:
    if name == "fake":
        return FakeEmbeddingProvider()
    from psyteardown.embed.local import LocalEmbeddingProvider

    return LocalEmbeddingProvider()


@app.command()
def analyze(
    input: Path = typer.Option(..., "--input", "-i", help="产品描述文本文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出文件;省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    use_memory: bool = typer.Option(False, "--use-memory", help="检索相似历史案例并注入分析"),
    no_save: bool = typer.Option(False, "--no-save", help="不把本次结果落盘案例库"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True),
):
    """拆解一个产品描述,输出结构化报告;默认落盘为案例。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)

    library = load_frameworks()
    llm = _build_provider(provider)

    emb: EmbeddingProvider | None = None
    case_store: CaseStore | None = None
    if use_memory or not no_save:
        emb = _build_embed_provider(embed_provider)
        case_store = CaseStore(store)

    prior_summary: str | None = None
    if use_memory and case_store is not None and emb is not None:
        hits = search_similar(case_store, emb, text, top_k=3)
        prior_summary = summarize_cases([c for c, _ in hits]) or None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = run_teardown(llm, text, library=library, generated_at=now,
                          prior_summary=prior_summary)

    rendered = render_json(result) if fmt == "json" else render_markdown(result)
    if out:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)

    if not no_save and case_store is not None and emb is not None:
        case = Case.from_result(result, description=text, created_at=now)
        case_store.save(case, emb.embed([text])[0])
        typer.echo(f"已落盘案例 {case.case_id}")


@app.command()
def similar(
    input: Path = typer.Option(..., "--input", "-i", help="产品描述文本文件"),
    top_k: int = typer.Option(3, "--top-k", help="返回最相似的前 K 个案例"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True),
):
    """检索与给定描述最相似的历史案例。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)
    emb = _build_embed_provider(embed_provider)
    case_store = CaseStore(store)
    hits = search_similar(case_store, emb, text, top_k=top_k)
    if not hits:
        typer.echo("案例库为空或无相似案例。")
        return
    for case, score in hits:
        fw = ", ".join(case.frameworks_used) or "—"
        typer.echo(f"{score:.3f}  {case.product_name} — {case.one_liner}  ({fw})")


@memory_app.command("stats")
def memory_stats(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """显示案例库统计。"""
    case_store = CaseStore(store)
    typer.echo(f"案例数:{case_store.count()}")


@kb_app.command("list")
def kb_list():
    """列出已加载的框架。"""
    for fw in load_frameworks():
        typer.echo(f"{fw.id}\t{fw.name}\t({fw.category})")


@kb_app.command("show")
def kb_show(framework_id: str = typer.Argument(..., help="框架 id")):
    """查看某框架详情。"""
    for fw in load_frameworks():
        if fw.id == framework_id:
            typer.echo(f"# {fw.name} ({fw.id})\n{fw.summary}\n")
            for p in fw.principles:
                typer.echo(f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})")
            return
    typer.echo(f"未找到框架:{framework_id}", err=True)
    raise typer.Exit(code=1)
```

- [ ] **Step 4: 运行,确认 PASS(5 passed)**

Run: `pytest tests/test_cli_memory.py -v`

- [ ] **Step 5: 全量回归 + 手动跑通**

Run: `pytest -q`
Expected: 全绿,`1 skipped`(v1 e2e)。

Run(手动验证 CLI 真实可用,用 fake 不触网):
```bash
printf '一个每日英语单词打卡 App,有连续打卡、推送提醒、好友排行榜。' > /tmp/p.txt
psyteardown analyze --input /tmp/p.txt --store /tmp/cases.db --out /tmp/r.md --provider fake --embed-provider fake
psyteardown similar --input /tmp/p.txt --store /tmp/cases.db --embed-provider fake
psyteardown memory stats --store /tmp/cases.db
```
Expected: analyze 落盘并提示 case id;similar 列出"样例产品";stats 显示"案例数:1"。

- [ ] **Step 6: 提交**

```bash
git add src/psyteardown/cli.py tests/test_cli_memory.py
git commit -m "feat: add memory CLI (analyze save/--use-memory, similar, memory stats)"
```

---

## Task 9: 可选嵌入冒烟测试 + README + 全量回归

**Files:**
- Create: `tests/test_smoke_embed_e2e.py`
- Modify: `README.md`

- [ ] **Step 1: 写可选冒烟测试(默认 skip)**

`tests/test_smoke_embed_e2e.py`:
```python
import os

import pytest

requires_e2e = pytest.mark.skipif(
    os.environ.get("PSYTEARDOWN_E2E") != "1",
    reason="需要 PSYTEARDOWN_E2E=1(会下载/加载本地嵌入模型)",
)


@requires_e2e
def test_local_embedding_real_model(tmp_path):
    from psyteardown.embed.local import LocalEmbeddingProvider
    from psyteardown.memory.store import CaseStore
    from psyteardown.memory.models import Case
    from psyteardown.memory.retrieval import search_similar
    from psyteardown.pipeline.schemas import (
        ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
    )

    def _case(desc, name):
        result = TeardownResult(
            product=ProductProfile(name=name, product_type="App",
                                   one_liner=name, features=[], touchpoints=[]),
            frameworks_used=["hook-model"], mappings=[],
            assessment=ExperienceAssessment(), executive_summary="s",
            meta=TeardownMeta(model="x", generated_at="t"),
        )
        return Case.from_result(result, description=desc, created_at="t")

    emb = LocalEmbeddingProvider()
    store = CaseStore(tmp_path / "c.db")
    for desc, name in [("每日签到打卡养成习惯", "签到App"),
                       ("股票基金理财投资", "理财App")]:
        store.save(_case(desc, name), emb.embed([desc])[0])

    hits = search_similar(store, emb, "打卡签到习惯养成", top_k=1)
    assert hits[0][0].product_name == "签到App"
```

- [ ] **Step 2: 确认默认 SKIP**

Run: `pytest tests/test_smoke_embed_e2e.py -v`
Expected: SKIPPED(1 skipped)。

- [ ] **Step 3: 更新 README**

把 `README.md` 的"用法"与"测试"段替换/补充为(在 v1 基础上加 v2 命令):
```markdown
## 用法

    export ANTHROPIC_API_KEY=sk-ant-...
    psyteardown analyze --input product.txt --format md  --out report.md
    psyteardown analyze --input product.txt --use-memory          # 注入相似历史案例
    psyteardown analyze --input product.txt --no-save             # 不落盘
    psyteardown similar --input product.txt --top-k 3             # 查相似历史案例
    psyteardown memory stats                                      # 案例库统计
    psyteardown kb list
    psyteardown kb show fogg-behavior-model

案例库默认存于 ./.psyteardown/cases.db(可用 --store 覆盖)。
向量检索默认用本地嵌入模型(需 `pip install -e ".[embed]"`,首次会下载模型);
不装 embed extra 时,仅 LLM 拆解可用,记忆/检索功能需要该 extra。

## 测试

    pytest                       # 全量(冒烟测试默认跳过,不触网、不加载模型)
    PSYTEARDOWN_E2E=1 pytest      # 含真实 Claude + 本地嵌入冒烟
```

- [ ] **Step 4: 全量回归**

Run: `pytest -q`
Expected: 全绿,`2 skipped`(v1 e2e + v2 embed e2e)。报告确切 `N passed, 2 skipped`。

- [ ] **Step 5: 提交**

```bash
git add tests/test_smoke_embed_e2e.py README.md
git commit -m "test: add optional local-embedding smoke test; document v2 in README"
```

---

## 自检:spec 覆盖核对

- 拆解后自动落盘案例(可 --no-save) → Task 8 ✅
- `similar` 检索命令 → Task 8 ✅
- 可插拔 EmbeddingProvider,默认本地模型 → Task 2/3 ✅
- SQLite 单文件,内容哈希 upsert 去重 → Task 4/5 ✅
- `--use-memory` 注入 step3、不污染 step1 → Task 7/8 ✅
- 全核心可脱离真实模型/网络测试(FakeEmbeddingProvider) → Task 2/5/6/7/8 ✅
- run_teardown 向后兼容(默认参数 = v1 行为) → Task 7 ✅
- 维度不匹配报错(MemoryStoreError) → Task 5/6 ✅
- YAGNI 不做项(第2/3层、托管嵌入、向量库等) → 计划未涉及,接口预留 ✅

**两处对 spec 的精化已固定**:嵌入对象 = 原始描述(删 embed_text.py);pipeline 收 prior_summary 字符串而非 Case(零 memory 依赖);异常名 MemoryStoreError(避内置)。
