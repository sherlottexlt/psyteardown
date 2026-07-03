# v3 语义记忆——框架知识增长 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让工具从积累的案例里提炼出现有框架盖不住的全新心理学框架,经人工审批后回填知识库。

**Architecture:** 新增 `growth` 子系统(候选模型、LLM 提炼、嵌入去重、YAML 候选/习得存储),扩展 `kb/loader` 合并种子 + 习得,CLI 加 `learn` / `candidates` 命令。复用 v1/v2 抽象(`LLMProvider`/`EmbeddingProvider`/`Framework`/YAML),全部核心离线可测(Fake)。

**Tech Stack:** 沿用 v1/v2(Python 3.11+、Pydantic v2、Typer、PyYAML、numpy)。无新增外部依赖。

> **对 spec 的两处落地精化(已固定):** `propose_frameworks` 增 `created_at` 参数(内核不调 datetime);`FrameworkCandidate.created_at`/`source_case_ids` 给默认值,使 LLM 结构化输出无需提供它们。

---

## 文件结构

```
src/psyteardown/
├── kb/loader.py                # 改:load_frameworks(directory=None, *, learned_dir=None)
├── growth/
│   ├── __init__.py             # 新(空)
│   ├── models.py               # 新:FrameworkCandidate + CandidateList
│   ├── store.py                # 新:GrowthStore + GrowthError
│   ├── proposer.py             # 新:propose_frameworks
│   └── dedup.py                # 新:filter_duplicates
└── cli.py                      # 改:learn + candidates 子命令;analyze/kb 合并 learned
tests/
├── growth/test_models.py       # 新
├── growth/test_store.py        # 新
├── growth/test_proposer.py     # 新
├── growth/test_dedup.py        # 新
├── kb/test_loader_learned.py   # 新
└── test_cli_growth.py          # 新
```

---

## Task 1: growth 候选模型

**Files:**
- Create: `src/psyteardown/growth/__init__.py` (空)
- Create: `src/psyteardown/growth/models.py`
- Create: `tests/growth/__init__.py` (空)
- Test: `tests/growth/test_models.py`

- [ ] **Step 1: 写失败测试**

`tests/growth/__init__.py`: 空。
`tests/growth/test_models.py`:
```python
from psyteardown.growth.models import FrameworkCandidate, CandidateList
from psyteardown.kb.models import Framework, Principle


def _fw(id_="dark-urgency"):
    return Framework(
        id=id_, name="虚假紧迫", category="persuasion", summary="制造人为时间压力促成即时决策。",
        tags=["紧迫", "转化"],
        principles=[Principle(id="p", name="倒计时", description="d", look_for=["倒计时"])],
        references=["r"],
    )


def test_candidate_defaults():
    c = FrameworkCandidate(framework=_fw(), rationale="现有框架未覆盖")
    assert c.source_case_ids == []
    assert c.created_at == ""
    assert c.framework.id == "dark-urgency"


def test_candidate_json_roundtrip():
    c = FrameworkCandidate(framework=_fw(), rationale="r",
                           source_case_ids=["a", "b"], created_at="t")
    again = FrameworkCandidate.model_validate_json(c.model_dump_json())
    assert again.source_case_ids == ["a", "b"]
    assert again.framework.name == "虚假紧迫"


def test_candidate_list_wraps():
    cl = CandidateList(candidates=[])
    assert cl.candidates == []
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/growth/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.growth'`

- [ ] **Step 3: 实现**

`src/psyteardown/growth/__init__.py`: 空。
`src/psyteardown/growth/models.py`:
```python
"""语义记忆增长:框架候选模型。"""

from pydantic import BaseModel, Field

from psyteardown.kb.models import Framework


class FrameworkCandidate(BaseModel):
    framework: Framework                              # 复用 v1 模型
    rationale: str                                    # 为什么现有框架盖不住
    source_case_ids: list[str] = Field(default_factory=list)
    created_at: str = ""                              # 调用方注入(LLM 无需提供)


class CandidateList(BaseModel):
    """messages.parse 顶层需 object。"""

    candidates: list[FrameworkCandidate] = Field(default_factory=list)
```

- [ ] **Step 4: 运行,确认 PASS(3 passed)**

Run: `pytest tests/growth/test_models.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/growth/__init__.py src/psyteardown/growth/models.py tests/growth/__init__.py tests/growth/test_models.py
git commit -m "feat: add FrameworkCandidate model"
```

---

## Task 2: GrowthStore(候选/习得 YAML 读写)

**Files:**
- Create: `src/psyteardown/growth/store.py`
- Test: `tests/growth/test_store.py`

- [ ] **Step 1: 写失败测试**

`tests/growth/test_store.py`:
```python
import pytest

from psyteardown.growth.models import FrameworkCandidate
from psyteardown.growth.store import GrowthStore, GrowthError
from psyteardown.kb.models import Framework, Principle


def _cand(id_="dark-urgency"):
    fw = Framework(
        id=id_, name="虚假紧迫", category="persuasion", summary="制造人为时间压力。",
        tags=["紧迫"],
        principles=[Principle(id="p", name="倒计时", description="d", look_for=["倒计时"])],
        references=["r"],
    )
    return FrameworkCandidate(framework=fw, rationale="现有框架未覆盖",
                              source_case_ids=["a", "b", "c"], created_at="t")


def test_save_and_list(tmp_path):
    store = GrowthStore(tmp_path)
    assert store.list_candidates() == []
    store.save_candidate(_cand())
    cands = store.list_candidates()
    assert len(cands) == 1
    assert cands[0].framework.id == "dark-urgency"


def test_get_candidate(tmp_path):
    store = GrowthStore(tmp_path)
    store.save_candidate(_cand())
    assert store.get_candidate("dark-urgency").rationale == "现有框架未覆盖"
    assert store.get_candidate("nope") is None


def test_approve_moves_to_learned(tmp_path):
    store = GrowthStore(tmp_path)
    store.save_candidate(_cand())
    path = store.approve("dark-urgency")
    assert path.exists()
    assert path.parent == store.learned_dir()
    assert store.get_candidate("dark-urgency") is None      # 候选已删
    # learned 里只存 framework(与种子同构),可被 kb loader 读
    from psyteardown.kb.loader import load_frameworks
    fws = load_frameworks(learned_dir=store.learned_dir())
    assert any(f.id == "dark-urgency" for f in fws)


def test_reject_deletes(tmp_path):
    store = GrowthStore(tmp_path)
    store.save_candidate(_cand())
    store.reject("dark-urgency")
    assert store.get_candidate("dark-urgency") is None


def test_approve_missing_raises(tmp_path):
    store = GrowthStore(tmp_path)
    with pytest.raises(GrowthError):
        store.approve("nope")


def test_reject_missing_raises(tmp_path):
    store = GrowthStore(tmp_path)
    with pytest.raises(GrowthError):
        store.reject("nope")
```

> 注:`test_approve_moves_to_learned` 依赖 Task 3 的 `load_frameworks(learned_dir=...)`。先实现 Task 2 让其余 5 个测试通过;`load_frameworks(learned_dir=...)` 尚不存在时该用例会失败——Task 3 完成后它自然转绿。执行时,若在 Task 2 阶段该用例因 `learned_dir` 关键字报 TypeError,属预期,Task 3 修复。

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/growth/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.growth.store'`

- [ ] **Step 3: 实现**

`src/psyteardown/growth/store.py`:
```python
"""候选/习得框架的 YAML 存储。候选待审;approve 后写习得层供 loader 合并。"""

from pathlib import Path

import yaml

from psyteardown.growth.models import FrameworkCandidate


class GrowthError(Exception):
    """候选/习得读写错误。"""


class GrowthStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._candidates = self.root / "candidates"
        self._learned = self.root / "learned"
        self._candidates.mkdir(parents=True, exist_ok=True)
        self._learned.mkdir(parents=True, exist_ok=True)

    def learned_dir(self) -> Path:
        return self._learned

    def save_candidate(self, cand: FrameworkCandidate) -> None:
        path = self._candidates / f"{cand.framework.id}.yaml"
        path.write_text(
            yaml.safe_dump(cand.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def list_candidates(self) -> list[FrameworkCandidate]:
        out: list[FrameworkCandidate] = []
        for p in sorted(self._candidates.glob("*.yaml")):
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
            out.append(FrameworkCandidate.model_validate(raw))
        return out

    def get_candidate(self, fid: str) -> FrameworkCandidate | None:
        p = self._candidates / f"{fid}.yaml"
        if not p.is_file():
            return None
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        return FrameworkCandidate.model_validate(raw)

    def approve(self, fid: str) -> Path:
        cand = self.get_candidate(fid)
        if cand is None:
            raise GrowthError(f"候选不存在: {fid}")
        dest = self._learned / f"{fid}.yaml"
        dest.write_text(
            yaml.safe_dump(cand.framework.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (self._candidates / f"{fid}.yaml").unlink()
        return dest

    def reject(self, fid: str) -> None:
        p = self._candidates / f"{fid}.yaml"
        if not p.is_file():
            raise GrowthError(f"候选不存在: {fid}")
        p.unlink()
```

- [ ] **Step 4: 运行(5 个通过,`test_approve_moves_to_learned` 待 Task 3)**

Run: `pytest tests/growth/test_store.py -v`
Expected: 5 passed;`test_approve_moves_to_learned` 可能因 `load_frameworks(learned_dir=...)` 尚未支持而 FAIL(Task 3 修复)。若想此刻全绿,可先做 Task 3 再回跑。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/growth/store.py tests/growth/test_store.py
git commit -m "feat: add GrowthStore (candidate/learned YAML store)"
```

---

## Task 3: loader 合并习得层

**Files:**
- Modify: `src/psyteardown/kb/loader.py`
- Test: `tests/kb/test_loader_learned.py`

- [ ] **Step 1: 写失败测试**

`tests/kb/test_loader_learned.py`:
```python
from psyteardown.kb.loader import load_frameworks

SEED = """
id: seed-fw
name: 种子框架
category: motivation
summary: s
tags: [x]
principles:
  - id: p
    name: p
    description: d
    look_for: [a]
references: [r]
"""

LEARNED = """
id: learned-fw
name: 习得框架
category: habit
summary: s2
tags: [y]
principles:
  - id: q
    name: q
    description: d
    look_for: [b]
references: [r2]
"""

# 与种子同 id,应被跳过(种子优先)
CLASH = SEED.replace("种子框架", "冒充者")


def _write(d, name, text):
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def test_no_learned_dir_matches_v1(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "seed-fw.yaml", SEED)
    fws = load_frameworks(seed)
    assert [f.id for f in fws] == ["seed-fw"]


def test_merges_learned(tmp_path):
    seed = tmp_path / "seed"
    learned = tmp_path / "learned"
    _write(seed, "seed-fw.yaml", SEED)
    _write(learned, "learned-fw.yaml", LEARNED)
    fws = load_frameworks(seed, learned_dir=learned)
    assert {f.id for f in fws} == {"seed-fw", "learned-fw"}


def test_seed_wins_on_id_clash(tmp_path):
    seed = tmp_path / "seed"
    learned = tmp_path / "learned"
    _write(seed, "seed-fw.yaml", SEED)
    _write(learned, "seed-fw.yaml", CLASH)     # 同 id
    fws = load_frameworks(seed, learned_dir=learned)
    got = [f for f in fws if f.id == "seed-fw"][0]
    assert got.name == "种子框架"              # 种子优先,冒充者被跳过
    assert len(fws) == 1


def test_missing_learned_dir_is_ok(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "seed-fw.yaml", SEED)
    fws = load_frameworks(seed, learned_dir=tmp_path / "nope")   # 不存在 → 忽略
    assert [f.id for f in fws] == ["seed-fw"]
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/kb/test_loader_learned.py -v`
Expected: FAIL — `TypeError: load_frameworks() got an unexpected keyword argument 'learned_dir'`

- [ ] **Step 3: 改 loader**

把 `src/psyteardown/kb/loader.py` 的 `load_frameworks` 整个函数替换为:
```python
def load_frameworks(
    directory: Path | None = None,
    *,
    learned_dir: Path | None = None,
) -> list[Framework]:
    """加载种子目录所有 *.yaml,按 id 升序返回;坏文件/坏 schema 抛 KBLoadError。
    若给 learned_dir 且存在,合并其中习得框架(与种子 id 冲突则跳过,种子优先)。"""
    directory = directory or DEFAULT_KB_DIR
    if not directory.is_dir():
        raise KBLoadError(f"知识库目录不存在: {directory}")

    frameworks: list[Framework] = []
    for path in sorted(directory.glob("*.yaml")):
        frameworks.append(_load_one(path))

    seed_ids = {f.id for f in frameworks}
    if learned_dir is not None and Path(learned_dir).is_dir():
        for path in sorted(Path(learned_dir).glob("*.yaml")):
            fw = _load_one(path)
            if fw.id in seed_ids:
                print(f"警告:习得框架 {fw.id} 与种子 id 冲突,已跳过(种子优先)。")
                continue
            frameworks.append(fw)

    frameworks.sort(key=lambda f: f.id)
    return frameworks


def _load_one(path: Path) -> Framework:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise KBLoadError(f"YAML 解析失败 {path.name}: {e}") from e
    try:
        return Framework.model_validate(raw)
    except ValidationError as e:
        raise KBLoadError(f"框架校验失败 {path.name}: {e}") from e
```

（保留文件顶部的 imports 与 `DEFAULT_KB_DIR`、`KBLoadError` 定义不变。）

- [ ] **Step 4: 运行,确认 PASS + Task 2 那条也转绿**

Run: `pytest tests/kb/test_loader_learned.py tests/growth/test_store.py -v`
Expected: 全部通过(含 `test_approve_moves_to_learned`)。

Run: `pytest -q`
Expected: 全绿,`2 skipped`(v1/v2 e2e)。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/loader.py tests/kb/test_loader_learned.py
git commit -m "feat: loader merges learned frameworks (seed wins on id clash)"
```

---

## Task 4: 提炼器 propose_frameworks

**Files:**
- Create: `src/psyteardown/growth/proposer.py`
- Test: `tests/growth/test_proposer.py`

- [ ] **Step 1: 写失败测试**

`tests/growth/test_proposer.py`:
```python
from psyteardown.growth.models import FrameworkCandidate, CandidateList
from psyteardown.growth.proposer import propose_frameworks
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.memory.models import Case
from psyteardown.pipeline.schemas import (
    ProductProfile, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _case(cid, one_liner):
    result = TeardownResult(
        product=ProductProfile(name=cid, product_type="App", one_liner=one_liner,
                               features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[Mapping(feature="f", framework_id="hook-model", principle_id="trigger",
                          rationale="r", evidence="每日推送", confidence=0.4)],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    c = Case.from_result(result, description=one_liner, created_at="t")
    c.case_id = cid          # Case 非 frozen,直接设定以便测试引用确定的 id
    return c


def _existing():
    return [Framework(id="hook-model", name="上瘾模型", category="habit",
                      summary="触发-行动-奖励-投入", tags=["习惯"],
                      principles=[Principle(id="trigger", name="触发", description="d")],
                      references=["r"])]


def _candidate(fid, support):
    fw = Framework(id=fid, name="新框架", category="emotion", summary="新机制",
                   tags=["x"],
                   principles=[Principle(id="p", name="p", description="d", look_for=["a"])],
                   references=["r"])
    return FrameworkCandidate(framework=fw, rationale="盖不住", source_case_ids=support)


def test_empty_cases_returns_empty():
    provider = FakeProvider()  # 空队列;空案例应直接返回,不调 LLM
    assert propose_frameworks(provider, [], _existing(), created_at="t") == []
    assert provider.calls == []


def test_existing_frameworks_in_prompt_and_stamps_created_at():
    cases = [_case(str(i), f"产品{i}") for i in range(3)]
    cand = _candidate("new-fw", support=["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CandidateList(candidates=[cand])])
    out = propose_frameworks(provider, cases, _existing(), created_at="2026-06-14", min_support=3)
    assert len(out) == 1
    assert out[0].created_at == "2026-06-14"
    assert "hook-model" in provider.calls[0]["prompt"]   # 现有框架进了 prompt


def test_filters_below_min_support():
    cases = [_case(str(i), f"产品{i}") for i in range(3)]
    weak = _candidate("weak", support=["0"])              # 仅 1 个支撑
    strong = _candidate("strong", support=["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CandidateList(candidates=[weak, strong])])
    out = propose_frameworks(provider, cases, _existing(), created_at="t", min_support=3)
    assert [c.framework.id for c in out] == ["strong"]


def test_drops_hallucinated_case_ids():
    cases = [_case(str(i), f"产品{i}") for i in range(3)]
    cand = _candidate("x", support=["0", "1", "999"])     # 999 不存在
    provider = FakeProvider(structured_responses=[CandidateList(candidates=[cand])])
    out = propose_frameworks(provider, cases, _existing(), created_at="t", min_support=3)
    assert out == []                                       # 有效支撑仅 2 个 < 3
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/growth/test_proposer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.growth.proposer'`

- [ ] **Step 3: 实现**

`src/psyteardown/growth/proposer.py`:
```python
"""从案例提炼现有框架盖不住的全新框架(结构化输出)。"""

from psyteardown.growth.models import CandidateList, FrameworkCandidate
from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMProvider
from psyteardown.memory.models import Case

_SYSTEM = (
    "你是心理学研究者,擅长从产品行为模式中归纳新的心理学框架。"
    "只在现有框架确实盖不住时才提出新框架,不要复述现有框架。"
)


def _existing_brief(existing: list[Framework]) -> str:
    return "\n".join(f"- {f.id}({f.name}):{f.summary}" for f in existing)


def _case_brief(cases: list[Case]) -> str:
    lines = []
    for c in cases:
        mech = "; ".join(
            f"{m.evidence}(置信{m.confidence:.1f})"
            for m in c.result.mappings
            if not m.error and m.evidence
        )
        lines.append(f"- [{c.case_id}] {c.one_liner}:{mech}")
    return "\n".join(lines)


def propose_frameworks(
    provider: LLMProvider,
    cases: list[Case],
    existing: list[Framework],
    *,
    created_at: str,
    min_support: int = 3,
    max_candidates: int = 5,
) -> list[FrameworkCandidate]:
    """空案例库 → []。要求候选引用 ≥min_support 个真实案例 id,否则丢弃。"""
    if not cases:
        return []
    prompt = (
        f"现有心理学框架(不要重复这些):\n{_existing_brief(existing)}\n\n"
        f"以下是若干产品的心理机制(每行含案例 id):\n{_case_brief(cases)}\n\n"
        "找出反复出现、且上述现有框架都无法很好解释的心理学模式,"
        f"提出至多 {max_candidates} 个全新框架。每个框架给出 id(kebab-case)、name、"
        "category、summary、tags、principles(每条含 id/name/description/look_for)、"
        "references、ethics_notes;在 rationale 说明为何现有框架盖不住,"
        f"在 source_case_ids 列出支撑它的案例 id(至少 {min_support} 个)。"
    )
    out = provider.structured_complete(prompt, CandidateList, system=_SYSTEM)
    valid = {c.case_id for c in cases}
    kept: list[FrameworkCandidate] = []
    for cand in out.candidates:
        support = [cid for cid in cand.source_case_ids if cid in valid]
        if len(support) < min_support:
            continue
        cand.source_case_ids = support
        cand.created_at = created_at
        kept.append(cand)
    return kept[:max_candidates]
```

- [ ] **Step 4: 运行,确认 PASS(4 passed)**

Run: `pytest tests/growth/test_proposer.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/growth/proposer.py tests/growth/test_proposer.py
git commit -m "feat: add framework proposer (gap detection from cases)"
```

---

## Task 5: 防重复 filter_duplicates

**Files:**
- Create: `src/psyteardown/growth/dedup.py`
- Test: `tests/growth/test_dedup.py`

- [ ] **Step 1: 写失败测试**

`tests/growth/test_dedup.py`:
```python
from psyteardown.embed.base import FakeEmbeddingProvider
from psyteardown.growth.dedup import filter_duplicates
from psyteardown.growth.models import FrameworkCandidate
from psyteardown.kb.models import Framework, Principle


def _fw(id_, name, summary):
    return Framework(id=id_, name=name, category="x", summary=summary, tags=["t"],
                     principles=[Principle(id="p", name="p", description="d")],
                     references=["r"])


def _cand(id_, name, summary):
    return FrameworkCandidate(framework=_fw(id_, name, summary), rationale="r")


def test_id_clash_dropped():
    existing = [_fw("dup", "已有", "已有摘要")]
    cands = [_cand("dup", "新名", "完全不同的摘要内容")]
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider())
    assert out == []


def test_name_clash_dropped():
    existing = [_fw("a", "同名框架", "摘要甲")]
    cands = [_cand("b", "同名框架", "摘要乙")]
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider())
    assert out == []


def test_semantically_similar_dropped():
    existing = [_fw("a", "框架甲", "签到打卡习惯养成推送提醒")]
    cands = [_cand("b", "框架乙", "签到打卡习惯养成推送")]     # 高度相似
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider(), threshold=0.9)
    assert out == []


def test_distinct_kept():
    existing = [_fw("a", "框架甲", "金融理财股票基金")]
    cands = [_cand("b", "框架乙", "签到打卡习惯养成推送")]
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider(), threshold=0.9)
    assert [c.framework.id for c in out] == ["b"]


def test_no_embed_falls_back_to_id_name_only():
    existing = [_fw("a", "框架甲", "签到打卡习惯养成推送提醒")]
    cands = [_cand("b", "框架乙", "签到打卡习惯养成推送")]     # 语义相似但 id/name 不同
    out = filter_duplicates(cands, existing, embed=None)      # 无嵌入 → 只按 id/name
    assert [c.framework.id for c in out] == ["b"]             # 相似但仍保留
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/growth/test_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.growth.dedup'`

- [ ] **Step 3: 实现**

`src/psyteardown/growth/dedup.py`:
```python
"""用嵌入相似度 + id/name 过滤掉与现有框架重复的候选。"""

import numpy as np

from psyteardown.embed.base import EmbeddingProvider
from psyteardown.growth.models import FrameworkCandidate
from psyteardown.kb.models import Framework


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    return float(a @ b / (na * nb)) if na and nb else 0.0


def filter_duplicates(
    candidates: list[FrameworkCandidate],
    existing: list[Framework],
    embed: EmbeddingProvider | None = None,
    *,
    threshold: float = 0.85,
) -> list[FrameworkCandidate]:
    """丢弃 id/name 与现有冲突的候选;若给 embed,再丢弃 summary 余弦 ≥threshold 的。
    embed 为 None(如离线)时只做 id/name 去重。"""
    existing_ids = {f.id for f in existing}
    existing_names = {f.name for f in existing}

    ex_vecs: list[np.ndarray] | None = None
    if embed is not None and existing:
        ex_vecs = [np.asarray(v, dtype=np.float32)
                   for v in embed.embed([f.summary for f in existing])]

    kept: list[FrameworkCandidate] = []
    for cand in candidates:
        fw = cand.framework
        if fw.id in existing_ids or fw.name in existing_names:
            continue
        if ex_vecs is not None:
            cv = np.asarray(embed.embed([fw.summary])[0], dtype=np.float32)
            if any(_cos(cv, ev) >= threshold for ev in ex_vecs):
                continue
        kept.append(cand)
    return kept
```

- [ ] **Step 4: 运行,确认 PASS(5 passed)**

Run: `pytest tests/growth/test_dedup.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/growth/dedup.py tests/growth/test_dedup.py
git commit -m "feat: add candidate dedup (embedding + id/name)"
```

---

## Task 6: CLI —— learn + candidates + 合并 learned

**Files:**
- Modify: `src/psyteardown/cli.py`
- Test: `tests/test_cli_growth.py`

> 说明:新增 `learn` 与 `candidates` 子命令;`analyze`/`kb list` 加载知识库时合并 `learned/`。growth 根目录取 `--store`(案例库路径)的父目录,与 `.psyteardown/` 布局一致。沿用 v1/v2 隐藏开关 `--provider fake` / `--embed-provider fake`。

- [ ] **Step 1: 写失败测试**

`tests/test_cli_growth.py`:
```python
from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()


def _seed_cases(tmp_path, n=3):
    """用 analyze(fake)在临时库里落 n 个案例。"""
    db = tmp_path / "cases.db"
    for i in range(n):
        src = tmp_path / f"p{i}.txt"
        src.write_text(f"产品{i}:每日签到推送提醒习惯养成 {i}", encoding="utf-8")
        r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                                "--out", str(tmp_path / f"r{i}.md"),
                                "--provider", "fake", "--embed-provider", "fake"])
        assert r.exit_code == 0, r.stdout
    return db


def test_learn_then_candidates_flow(tmp_path, monkeypatch):
    db = _seed_cases(tmp_path)

    # 注入一个固定候选(引用真实案例 id)——避免依赖真实 LLM
    import psyteardown.cli as cli
    from psyteardown.growth.models import FrameworkCandidate, CandidateList
    from psyteardown.kb.models import Framework, Principle
    from psyteardown.memory.store import CaseStore

    ids = [c.case_id for c, _ in CaseStore(db).all()]
    cand = FrameworkCandidate(
        framework=Framework(id="novelty-loop", name="新奇回路", category="emotion",
                            summary="用不可预期的新奇刺激维持回访", tags=["新奇"],
                            principles=[Principle(id="p", name="p", description="d", look_for=["随机"])],
                            references=["r"]),
        rationale="现有框架未覆盖新奇驱动", source_case_ids=ids)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CandidateList(candidates=[cand])))

    # learn
    r = runner.invoke(app, ["learn", "--store", str(db), "--min-support", "1",
                            "--provider", "fake", "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout

    # list
    r = runner.invoke(app, ["candidates", "list", "--store", str(db)])
    assert "novelty-loop" in r.stdout

    # approve → 之后 kb list 应包含它
    r = runner.invoke(app, ["candidates", "approve", "novelty-loop", "--store", str(db)])
    assert r.exit_code == 0, r.stdout
    r = runner.invoke(app, ["kb", "list", "--store", str(db)])
    assert "novelty-loop" in r.stdout


def test_candidates_reject(tmp_path, monkeypatch):
    db = _seed_cases(tmp_path, n=1)
    import psyteardown.cli as cli
    from psyteardown.growth.models import FrameworkCandidate, CandidateList
    from psyteardown.kb.models import Framework, Principle
    from psyteardown.memory.store import CaseStore

    ids = [c.case_id for c, _ in CaseStore(db).all()]
    cand = FrameworkCandidate(
        framework=Framework(id="temp-fw", name="临时", category="x", summary="s",
                            tags=["t"], principles=[Principle(id="p", name="p", description="d")],
                            references=["r"]),
        rationale="r", source_case_ids=ids)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CandidateList(candidates=[cand])))
    runner.invoke(app, ["learn", "--store", str(db), "--min-support", "1",
                        "--provider", "fake", "--embed-provider", "fake"])
    r = runner.invoke(app, ["candidates", "reject", "temp-fw", "--store", str(db)])
    assert r.exit_code == 0
    r = runner.invoke(app, ["candidates", "list", "--store", str(db)])
    assert "temp-fw" not in r.stdout


class _FakeLLM:
    """只实现 structured_complete,返回预置结构;够 learn 用。"""
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self._payload

    def complete(self, prompt, *, system=None):
        return ""
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/test_cli_growth.py -v`
Expected: FAIL — 无 `learn` / `candidates` 命令(exit≠0 或 usage error)。

- [ ] **Step 3: 改 CLI**

在 `src/psyteardown/cli.py` 中做以下改动:

(a) 顶部新增 imports:
```python
from psyteardown.growth.store import GrowthStore
from psyteardown.growth.proposer import propose_frameworks
from psyteardown.growth.dedup import filter_duplicates
```

(b) 新增 candidates 子应用(在 `memory_app` 定义之后):
```python
candidates_app = typer.Typer(help="习得框架候选:审阅/批准/驳回")
app.add_typer(candidates_app, name="candidates")


def _growth_store(store: Path) -> GrowthStore:
    return GrowthStore(store.parent)
```

(c) `analyze` 里两处 `load_frameworks()` 调用改为合并 learned。把 analyze 内的
```python
    library = load_frameworks()
```
改为:
```python
    library = load_frameworks(learned_dir=_growth_store(store).learned_dir())
```

(d) `kb_list` 需要感知 learned,给它加 `--store` 选项:
把 `kb_list` 整个替换为:
```python
@kb_app.command("list")
def kb_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径(用于合并习得框架)"),
):
    """列出已加载的框架(含已批准的习得框架)。"""
    for fw in load_frameworks(learned_dir=_growth_store(store).learned_dir()):
        typer.echo(f"{fw.id}\t{fw.name}\t({fw.category})")
```

(e) 新增 `learn` 命令与 candidates 子命令(放在文件末尾):
```python
@app.command()
def learn(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    min_support: int = typer.Option(3, "--min-support", help="候选需的最少支撑案例数"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True),
):
    """从案例库提炼现有框架盖不住的候选新框架(待人工审批)。"""
    cases = [c for c, _ in CaseStore(store).all()]
    if not cases:
        typer.echo("案例库为空,先用 analyze 积累案例再 learn。")
        return
    gstore = _growth_store(store)
    existing = load_frameworks(learned_dir=gstore.learned_dir())
    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cands = propose_frameworks(llm, cases, existing, created_at=now,
                               min_support=min_support)

    # 去重(嵌入是增强;不可用则降级为 id/name 去重)
    emb: EmbeddingProvider | None = None
    try:
        emb = _build_embed_provider(embed_provider)
        emb.embed(["预热"])  # 触发懒加载,离线会在此失败
    except Exception as e:  # noqa: BLE001
        typer.echo(f"提示:嵌入不可用({e}),去重降级为 id/name。", err=True)
        emb = None
    cands = filter_duplicates(cands, existing, embed=emb)

    for cand in cands:
        gstore.save_candidate(cand)
    typer.echo(f"提炼出 {len(cands)} 个候选框架(待审):"
               + ", ".join(c.framework.id for c in cands))


@candidates_app.command("list")
def candidates_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """列出待审候选框架。"""
    cands = _growth_store(store).list_candidates()
    if not cands:
        typer.echo("无候选。")
        return
    for c in cands:
        typer.echo(f"{c.framework.id}\t{c.framework.name}\t(支撑 {len(c.source_case_ids)} 例)")


@candidates_app.command("show")
def candidates_show(
    framework_id: str = typer.Argument(..., help="候选框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """查看候选详情。"""
    c = _growth_store(store).get_candidate(framework_id)
    if c is None:
        typer.echo(f"候选不存在:{framework_id}", err=True)
        raise typer.Exit(code=1)
    fw = c.framework
    typer.echo(f"# {fw.name} ({fw.id}) — {fw.category}\n{fw.summary}\n")
    typer.echo(f"提案理由:{c.rationale}")
    typer.echo(f"支撑案例:{', '.join(c.source_case_ids)}\n")
    for p in fw.principles:
        typer.echo(f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})")


@candidates_app.command("approve")
def candidates_approve(
    framework_id: str = typer.Argument(..., help="候选框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """批准候选,写入习得层(此后 analyze 生效)。"""
    from psyteardown.growth.store import GrowthError

    try:
        path = _growth_store(store).approve(framework_id)
    except GrowthError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已批准 {framework_id} → {path}")


@candidates_app.command("reject")
def candidates_reject(
    framework_id: str = typer.Argument(..., help="候选框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """驳回并删除候选。"""
    from psyteardown.growth.store import GrowthError

    try:
        _growth_store(store).reject(framework_id)
    except GrowthError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已驳回 {framework_id}")
```

- [ ] **Step 4: 运行,确认 PASS(2 passed)**

Run: `pytest tests/test_cli_growth.py -v`

- [ ] **Step 5: 全量回归**

Run: `pytest -q`
Expected: 全绿,`2 skipped`(v1/v2 e2e)。

- [ ] **Step 6: 提交**

```bash
git add src/psyteardown/cli.py tests/test_cli_growth.py
git commit -m "feat: add learn + candidates CLI; analyze/kb merge learned frameworks"
```

---

## Task 7: README + 全量回归

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README**

把 `README.md` 的"用法"段中,`## 用法` 下补充 v3 命令(在 `memory stats` 行之后、`kb list` 行之前插入):
```markdown
    psyteardown learn                                            # 从案例提炼候选新框架(待审)
    psyteardown candidates list                                  # 列候选
    psyteardown candidates show <id>                             # 看候选详情
    psyteardown candidates approve <id>                          # 批准入库(此后 analyze 生效)
    psyteardown candidates reject <id>                           # 驳回
```

并把顶部标题行与"架构"段更新:标题 `# psyteardown — 心理驱动型产品拆解 Agent(v3)`;架构小节追加一行:
```markdown
- `growth` — 语义记忆:从案例提炼候选新框架,人工审批后回填知识库(种子库永不被动)
```

- [ ] **Step 2: 全量回归**

Run: `pytest -q`
Expected: 全绿,`2 skipped`。报告确切 `N passed, 2 skipped`。

- [ ] **Step 3: 手动跑通(fake,不触网)**

```bash
printf '每日单词打卡App,连续天数、推送、排行榜、限时挑战' > /tmp/p.txt
psyteardown analyze --input /tmp/p.txt --store /tmp/c.db --out /tmp/r.md --provider fake --embed-provider fake
psyteardown kb list --store /tmp/c.db
```
Expected: analyze 落盘;kb list 列出种子框架(暂无习得)。

- [ ] **Step 4: 提交**

```bash
git add README.md
git commit -m "docs: document v3 learn/candidates commands in README"
```

---

## 自检:spec 覆盖核对

- `learn` 提炼候选新框架 → Task 4 + Task 6 ✅
- 人工审批(list/show/approve/reject) → Task 2 + Task 6 ✅
- 种子库永不被动;approve 才写习得;种子 id 优先 → Task 2 + Task 3 ✅
- 三道质量闸(现有框架入 prompt + min_support / 嵌入去重 / 人工审批) → Task 4 + Task 5 + Task 6 ✅
- 复用 LLMProvider/EmbeddingProvider/Framework/YAML,离线可测 → 全任务用 Fake ✅
- load_frameworks 向后兼容(不传 learned_dir = v1/v2 行为) → Task 3 ✅
- 嵌入不可用降级 → Task 5(filter_duplicates embed=None)+ Task 6(learn try/except) ✅
- YAGNI 不做项(自动触发/新 look_for 粒度/第3层/自动入库) → 计划未涉及 ✅

**两处对 spec 的精化已固定**:`propose_frameworks` 增 `created_at` 参数;`FrameworkCandidate` 的 `created_at`/`source_case_ids` 给默认值。
