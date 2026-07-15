# v4 程序性记忆——策略卡 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让工具反思过去的拆解、沉淀启发式策略卡,经人工审批后按步骤注入未来的拆解流程。

**Architecture:** 新增 `strategy` 子系统(策略卡模型、跨案例提炼、复盘蒸馏、YAML 候选/已批准存储、按步选择器),对 pipeline step3/step4 加可选 `strategy_guidance` 注入,CLI 加 `strategize`/`reflect`/`strategies`/`analyze --use-strategies`。复用 v1/v2/v3 抽象,全部核心离线可测。

**Tech Stack:** 沿用既有(Python 3.11+、Pydantic v2、Typer、PyYAML、numpy)。无新增外部依赖。

---

## 文件结构

```
src/psyteardown/
├── strategy/
│   ├── __init__.py             # 新(空)
│   ├── models.py               # 新:StrategyCard + CardList
│   ├── store.py                # 新:StrategyStore + StrategyError
│   ├── select.py               # 新:select_for(cards, profile, step) → 指引文本
│   ├── proposer.py             # 新:propose_strategies(跨案例)
│   └── distill.py              # 新:distill_from_note(复盘)
├── pipeline/
│   ├── steps.py                # 改:map_features/assess_experience 加 strategy_guidance
│   └── orchestrator.py         # 改:run_teardown 加 strategy_cards,分发
└── cli.py                      # 改:strategize/reflect/strategies;analyze --use-strategies
tests/
├── strategy/__init__.py        # 新(空)
├── strategy/test_models.py     # 新
├── strategy/test_store.py      # 新
├── strategy/test_select.py     # 新
├── strategy/test_proposer.py   # 新
├── strategy/test_distill.py    # 新
├── pipeline/test_steps_strategy.py     # 新
└── test_cli_strategy.py        # 新
```

---

## Task 1: StrategyCard 模型

**Files:**
- Create: `src/psyteardown/strategy/__init__.py` (空)
- Create: `src/psyteardown/strategy/models.py`
- Create: `tests/strategy/__init__.py` (空)
- Test: `tests/strategy/test_models.py`

- [ ] **Step 1: 写失败测试**

`tests/strategy/__init__.py`: 空。
`tests/strategy/test_models.py`:
```python
from psyteardown.strategy.models import StrategyCard, CardList


def _card(id_="prefer-social-proof"):
    return StrategyCard(id=id_, rule="社交产品必查社交证明相关框架",
                        rationale="社交类案例中社交证明反复高置信命中",
                        target_step="retrieval", applies_to=["社交", "社区"],
                        source_case_ids=["a", "b", "c"], created_at="t")


def test_card_defaults():
    c = StrategyCard(id="x", rule="r", rationale="why", target_step="mapping")
    assert c.applies_to == []
    assert c.source_case_ids == []
    assert c.created_at == ""


def test_card_json_roundtrip():
    c = _card()
    again = StrategyCard.model_validate_json(c.model_dump_json())
    assert again.target_step == "retrieval"
    assert again.applies_to == ["社交", "社区"]


def test_card_list_wraps():
    assert CardList(cards=[]).cards == []
    assert CardList().cards == []
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/strategy/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.strategy'`

- [ ] **Step 3: 实现**

`src/psyteardown/strategy/__init__.py`: 空。
`src/psyteardown/strategy/models.py`:
```python
"""程序性记忆:拆解策略卡。"""

from pydantic import BaseModel, Field


class StrategyCard(BaseModel):
    id: str                                   # kebab-case,唯一;做文件名
    rule: str                                 # 启发式本身
    rationale: str                            # 依据(从哪些案例规律归纳)
    target_step: str                          # retrieval | mapping | assessment
    applies_to: list[str] = Field(default_factory=list)      # 品类命中词;空=通配
    source_case_ids: list[str] = Field(default_factory=list) # 支撑案例(复盘可空)
    created_at: str = ""                      # 调用方注入


class CardList(BaseModel):
    """messages.parse 顶层需 object。"""

    cards: list[StrategyCard] = Field(default_factory=list)
```

- [ ] **Step 4: 运行,确认 PASS(3 passed)**

Run: `pytest tests/strategy/test_models.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/strategy/__init__.py src/psyteardown/strategy/models.py tests/strategy/__init__.py tests/strategy/test_models.py
git commit -m "feat: add StrategyCard model"
```

---

## Task 2: StrategyStore(候选/已批准 YAML + 台账)

**Files:**
- Create: `src/psyteardown/strategy/store.py`
- Test: `tests/strategy/test_store.py`

- [ ] **Step 1: 写失败测试**

`tests/strategy/test_store.py`:
```python
import pytest

from psyteardown.strategy.models import StrategyCard
from psyteardown.strategy.store import StrategyStore, StrategyError


def _card(id_="prefer-social-proof"):
    return StrategyCard(id=id_, rule="社交产品必查社交证明", rationale="why",
                        target_step="retrieval", applies_to=["社交"],
                        source_case_ids=["a", "b", "c"], created_at="t")


def test_save_and_list(tmp_path):
    store = StrategyStore(tmp_path)
    assert store.list_candidates() == []
    store.save_candidate(_card())
    cards = store.list_candidates()
    assert len(cards) == 1
    assert cards[0].id == "prefer-social-proof"


def test_get_candidate(tmp_path):
    store = StrategyStore(tmp_path)
    store.save_candidate(_card())
    assert store.get_candidate("prefer-social-proof").rule == "社交产品必查社交证明"
    assert store.get_candidate("nope") is None


def test_approve_moves_to_approved(tmp_path):
    store = StrategyStore(tmp_path)
    store.save_candidate(_card())
    path = store.approve("prefer-social-proof")
    assert path.exists()
    assert path.parent == store.approved_dir()
    assert store.get_candidate("prefer-social-proof") is None      # 候选已删
    approved = store.list_approved()
    assert [c.id for c in approved] == ["prefer-social-proof"]


def test_reject_records_and_save_skips(tmp_path):
    store = StrategyStore(tmp_path)
    store.save_candidate(_card())
    store.reject("prefer-social-proof")
    assert store.is_rejected("prefer-social-proof")
    store.save_candidate(_card())                                  # 同 id 不复活
    assert store.get_candidate("prefer-social-proof") is None


def test_invalid_id_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.save_candidate(_card("../evil"))


def test_approve_missing_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.approve("nope")


def test_reject_missing_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.reject("nope")
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/strategy/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.strategy.store'`

- [ ] **Step 3: 实现**

`src/psyteardown/strategy/store.py`:
```python
"""策略卡的 YAML 存储:候选待审;approve 后写已批准层供注入。仿 v3 GrowthStore。"""

import re
from pathlib import Path

import yaml

from psyteardown.strategy.models import StrategyCard

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class StrategyError(Exception):
    """策略卡读写或一致性错误。"""


def _check_id(sid: str) -> str:
    if not _ID_RE.match(sid):
        raise StrategyError(f"非法策略 id(仅允许字母/数字/_/-): {sid!r}")
    return sid


class StrategyStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._candidates = self.root / "strategy_candidates"
        self._approved = self.root / "strategies"
        self._rejected = self.root / "strategies_rejected.txt"
        self._candidates.mkdir(parents=True, exist_ok=True)
        self._approved.mkdir(parents=True, exist_ok=True)

    def approved_dir(self) -> Path:
        return self._approved

    def _rejected_ids(self) -> set[str]:
        if not self._rejected.is_file():
            return set()
        return {ln.strip() for ln in self._rejected.read_text(encoding="utf-8").splitlines() if ln.strip()}

    def is_rejected(self, sid: str) -> bool:
        return sid in self._rejected_ids()

    def _read(self, path: Path) -> StrategyCard:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return StrategyCard.model_validate(raw)

    def save_candidate(self, card: StrategyCard) -> None:
        sid = _check_id(card.id)
        if self.is_rejected(sid):
            return
        (self._candidates / f"{sid}.yaml").write_text(
            yaml.safe_dump(card.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def list_candidates(self) -> list[StrategyCard]:
        return [self._read(p) for p in sorted(self._candidates.glob("*.yaml"))]

    def list_approved(self) -> list[StrategyCard]:
        return [self._read(p) for p in sorted(self._approved.glob("*.yaml"))]

    def get_candidate(self, sid: str) -> StrategyCard | None:
        p = self._candidates / f"{sid}.yaml"
        return self._read(p) if p.is_file() else None

    def approve(self, sid: str) -> Path:
        _check_id(sid)
        card = self.get_candidate(sid)
        if card is None:
            raise StrategyError(f"候选不存在: {sid}")
        dest = self._approved / f"{sid}.yaml"
        dest.write_text(
            yaml.safe_dump(card.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (self._candidates / f"{sid}.yaml").unlink()
        return dest

    def reject(self, sid: str) -> None:
        _check_id(sid)
        p = self._candidates / f"{sid}.yaml"
        if not p.is_file():
            raise StrategyError(f"候选不存在: {sid}")
        p.unlink()
        with self._rejected.open("a", encoding="utf-8") as f:
            f.write(f"{sid}\n")
```

- [ ] **Step 4: 运行,确认 PASS(7 passed)**

Run: `pytest tests/strategy/test_store.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/strategy/store.py tests/strategy/test_store.py
git commit -m "feat: add StrategyStore (candidate/approved YAML + reject ledger)"
```

---

## Task 3: 选择器 select_for(按步 + applies_to 分发)

**Files:**
- Create: `src/psyteardown/strategy/select.py`
- Test: `tests/strategy/test_select.py`

- [ ] **Step 1: 写失败测试**

`tests/strategy/test_select.py`:
```python
from psyteardown.strategy.models import StrategyCard
from psyteardown.strategy.select import select_for
from psyteardown.pipeline.schemas import ProductProfile, Feature


def _profile(ptype="社交App", features=("动态",)):
    return ProductProfile(name="Demo", product_type=ptype, one_liner="x",
                          features=[Feature(name=f, description="d", user_goal="g") for f in features],
                          touchpoints=[])


def _card(id_, step, applies=()):
    return StrategyCard(id=id_, rule=f"规则{id_}", rationale="r",
                        target_step=step, applies_to=list(applies))


def test_empty_cards_returns_empty():
    assert select_for([], _profile(), "mapping") == ""


def test_mapping_step_selects_mapping_and_retrieval():
    cards = [_card("m", "mapping"), _card("r", "retrieval"), _card("a", "assessment")]
    out = select_for(cards, _profile(), "mapping")
    assert "规则m" in out
    assert "规则r" in out          # retrieval 并入 mapping
    assert "检索层建议" in out       # retrieval 标注
    assert "规则a" not in out       # assessment 不串台


def test_assessment_step_only_assessment():
    cards = [_card("m", "mapping"), _card("a", "assessment")]
    out = select_for(cards, _profile(), "assessment")
    assert "规则a" in out
    assert "规则m" not in out


def test_applies_to_wildcard_when_empty():
    cards = [_card("m", "mapping", applies=())]      # 空 = 通配
    assert "规则m" in select_for(cards, _profile(ptype="理财App"), "mapping")


def test_applies_to_hit_by_substring():
    cards = [_card("m", "mapping", applies=["社交"])]
    assert "规则m" in select_for(cards, _profile(ptype="社交App"), "mapping")


def test_applies_to_miss_excluded():
    cards = [_card("m", "mapping", applies=["理财"])]
    assert select_for(cards, _profile(ptype="社交App", features=("动态",)), "mapping") == ""
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/strategy/test_select.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.strategy.select'`

- [ ] **Step 3: 实现**

`src/psyteardown/strategy/select.py`:
```python
"""按 target_step + applies_to 选出适用策略卡,拼成注入指引文本。纯代码。"""

from psyteardown.strategy.models import StrategyCard
from psyteardown.pipeline.schemas import ProductProfile

_VALID_STEPS = ("retrieval", "mapping", "assessment")


def _applies(card: StrategyCard, profile: ProductProfile) -> bool:
    if not card.applies_to:
        return True                      # 空 = 通配
    haystacks = [profile.product_type] + [f.name for f in profile.features]
    for term in card.applies_to:
        for h in haystacks:
            if term in h or h in term:   # 子串双向匹配(同 v1 检索器风格)
                return True
    return False


def select_for(cards: list[StrategyCard], profile: ProductProfile, step: str) -> str:
    """step=="mapping" 时并入 retrieval 类(标注「检索层建议」);
    step=="assessment" 只取 assessment 类。applies_to 命中当前产品才入选。无命中→''。"""
    wanted = {step}
    if step == "mapping":
        wanted.add("retrieval")
    lines: list[str] = []
    for c in cards:
        if c.target_step not in wanted or not _applies(c, profile):
            continue
        tag = "(检索层建议)" if c.target_step == "retrieval" else ""
        lines.append(f"- {c.rule}{tag}")
    return "\n".join(lines)
```

- [ ] **Step 4: 运行,确认 PASS(6 passed)**

Run: `pytest tests/strategy/test_select.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/strategy/select.py tests/strategy/test_select.py
git commit -m "feat: add strategy selector (target_step + applies_to dispatch)"
```

---

## Task 4: 跨案例提炼 propose_strategies

**Files:**
- Create: `src/psyteardown/strategy/proposer.py`
- Test: `tests/strategy/test_proposer.py`

- [ ] **Step 1: 写失败测试**

`tests/strategy/test_proposer.py`:
```python
from psyteardown.strategy.models import StrategyCard, CardList
from psyteardown.strategy.proposer import propose_strategies
from psyteardown.llm.base import FakeProvider
from psyteardown.memory.models import Case
from psyteardown.pipeline.schemas import (
    ProductProfile, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _case(cid, ptype="社交App"):
    result = TeardownResult(
        product=ProductProfile(name=cid, product_type=ptype, one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[Mapping(feature="f", framework_id="hook-model", principle_id="trigger",
                          rationale="r", evidence="e", confidence=0.9)],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    c = Case.from_result(result, description=f"{cid} {ptype}", created_at="t")
    c.case_id = cid
    return c


def _card(id_, support, step="mapping"):
    return StrategyCard(id=id_, rule="r", rationale="why", target_step=step,
                        source_case_ids=support)


def test_empty_cases_returns_empty():
    provider = FakeProvider()
    assert propose_strategies(provider, [], created_at="t") == []
    assert provider.calls == []


def test_stamps_created_at_and_summary_in_prompt():
    cases = [_case(str(i)) for i in range(3)]
    card = _card("prefer-x", ["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = propose_strategies(provider, cases, created_at="2026-07-08", min_support=3)
    assert len(out) == 1
    assert out[0].created_at == "2026-07-08"
    assert "hook-model" in provider.calls[0]["prompt"]   # 统计摘要进 prompt


def test_filters_below_min_support():
    cases = [_case(str(i)) for i in range(3)]
    weak = _card("weak", ["0"])
    strong = _card("strong", ["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CardList(cards=[weak, strong])])
    out = propose_strategies(provider, cases, created_at="t", min_support=3)
    assert [c.id for c in out] == ["strong"]


def test_drops_hallucinated_case_ids():
    cases = [_case(str(i)) for i in range(3)]
    card = _card("x", ["0", "1", "999"])
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = propose_strategies(provider, cases, created_at="t", min_support=3)
    assert out == []


def test_drops_invalid_target_step():
    cases = [_case(str(i)) for i in range(3)]
    bad = _card("bad", ["0", "1", "2"], step="synthesis")   # 非法枚举
    provider = FakeProvider(structured_responses=[CardList(cards=[bad])])
    out = propose_strategies(provider, cases, created_at="t", min_support=3)
    assert out == []
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/strategy/test_proposer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.strategy.proposer'`

- [ ] **Step 3: 实现**

`src/psyteardown/strategy/proposer.py`:
```python
"""跨案例模式:从案例统计规律归纳启发式策略卡(结构化输出)。"""

from psyteardown.strategy.models import CardList, StrategyCard
from psyteardown.strategy.select import _VALID_STEPS
from psyteardown.llm.base import LLMProvider
from psyteardown.memory.models import Case

_SYSTEM = (
    "你是产品拆解方法论专家,擅长从大量拆解案例中归纳「怎么拆得更好」的启发式。"
    "只提出有案例支撑、可操作的策略,不要空泛口号。"
)


def _case_brief(cases: list[Case]) -> str:
    lines = []
    for c in cases:
        mech = "; ".join(
            f"{m.framework_id}.{m.principle_id}(置信{m.confidence:.1f}"
            + (",失败" if m.error else "") + ")"
            for m in c.result.mappings
        )
        lines.append(f"- [{c.case_id}] {c.product_name}({c.result.product.product_type}):{mech}")
    return "\n".join(lines)


def propose_strategies(
    provider: LLMProvider,
    cases: list[Case],
    *,
    created_at: str,
    min_support: int = 3,
    max_cards: int = 5,
) -> list[StrategyCard]:
    """空案例→[]。要求每卡引用 ≥min_support 真实案例、target_step 合法,否则丢弃。"""
    if not cases:
        return []
    prompt = (
        "以下是历史拆解案例的心理机制命中情况(含产品类型、框架·原则、置信度、是否失败):\n"
        f"{_case_brief(cases)}\n\n"
        "请归纳「怎么拆得更好」的启发式策略卡:哪些框架在哪类产品上稳定高置信、"
        "哪些总是低置信或失败、下次遇到该类产品应如何调整。每张卡给出 id(kebab-case)、"
        "rule(可操作的启发式)、rationale(依据)、target_step(retrieval/mapping/assessment 之一)、"
        "applies_to(适用的产品类型/品类词,通用可留空)、source_case_ids(支撑它的案例 id,"
        f"至少 {min_support} 个)。至多 {max_cards} 张。"
    )
    out = provider.structured_complete(prompt, CardList, system=_SYSTEM)
    valid = {c.case_id for c in cases}
    kept: list[StrategyCard] = []
    for card in out.cards:
        if card.target_step not in _VALID_STEPS:
            continue
        support = [cid for cid in card.source_case_ids if cid in valid]
        if len(support) < min_support:
            continue
        card.source_case_ids = support
        card.created_at = created_at
        kept.append(card)
    return kept[:max_cards]
```

- [ ] **Step 4: 运行,确认 PASS(5 passed)**

Run: `pytest tests/strategy/test_proposer.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/strategy/proposer.py tests/strategy/test_proposer.py
git commit -m "feat: add strategy proposer (cross-case heuristic distillation)"
```

---

## Task 5: 复盘蒸馏 distill_from_note(副入口)

**Files:**
- Create: `src/psyteardown/strategy/distill.py`
- Test: `tests/strategy/test_distill.py`

- [ ] **Step 1: 写失败测试**

`tests/strategy/test_distill.py`:
```python
from psyteardown.strategy.models import StrategyCard, CardList
from psyteardown.strategy.distill import distill_from_note
from psyteardown.llm.base import FakeProvider


def _card(id_, step="mapping"):
    return StrategyCard(id=id_, rule="社交产品别漏社交证明", rationale="人工复盘",
                        target_step=step, applies_to=["社交"])   # 无 source_case_ids


def test_empty_note_returns_empty():
    provider = FakeProvider()
    assert distill_from_note(provider, "  ", created_at="t") == []
    assert provider.calls == []


def test_note_in_prompt_and_stamps_created_at():
    card = _card("no-social-proof")
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = distill_from_note(provider, "社交产品别漏社交证明", created_at="2026-07-08")
    assert len(out) == 1
    assert out[0].created_at == "2026-07-08"
    assert "社交产品别漏社交证明" in provider.calls[0]["prompt"]


def test_keeps_card_without_source_cases():
    card = _card("x")
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = distill_from_note(provider, "note", created_at="t")
    assert out[0].source_case_ids == []      # 人工复盘豁免 min_support


def test_drops_invalid_target_step():
    card = _card("bad", step="synthesis")
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    assert distill_from_note(provider, "note", created_at="t") == []
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/strategy/test_distill.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.strategy.distill'`

- [ ] **Step 3: 实现**

`src/psyteardown/strategy/distill.py`:
```python
"""副入口:把用户自然语言复盘蒸馏成策略卡。豁免案例支撑。"""

from psyteardown.strategy.models import CardList, StrategyCard
from psyteardown.strategy.select import _VALID_STEPS
from psyteardown.llm.base import LLMProvider

_SYSTEM = (
    "你把用户对产品拆解的复盘笔记结构化成可复用的策略卡,忠实于用户原意,不臆造。"
)


def distill_from_note(provider: LLMProvider, note: str, *, created_at: str) -> list[StrategyCard]:
    """空 note→[]。target_step 非法的卡丢弃;source_case_ids 允许为空(人工输入)。"""
    if not note or not note.strip():
        return []
    prompt = (
        f"用户的拆解复盘笔记:\n{note}\n\n"
        "请把它结构化成 1 到多张策略卡。每张给出 id(kebab-case)、rule(可操作启发式)、"
        "rationale(依据,可引用用户原话)、target_step(retrieval/mapping/assessment 之一)、"
        "applies_to(适用产品类型/品类词,通用可留空)。无需 source_case_ids。"
    )
    out = provider.structured_complete(prompt, CardList, system=_SYSTEM)
    kept: list[StrategyCard] = []
    for card in out.cards:
        if card.target_step not in _VALID_STEPS:
            continue
        card.created_at = created_at
        kept.append(card)
    return kept
```

- [ ] **Step 4: 运行,确认 PASS(4 passed)**

Run: `pytest tests/strategy/test_distill.py -v`

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/strategy/distill.py tests/strategy/test_distill.py
git commit -m "feat: add note distillation (manual reflection entry point)"
```

---

## Task 6: 流水线注入(step3/step4 + orchestrator)

**Files:**
- Modify: `src/psyteardown/pipeline/steps.py`
- Modify: `src/psyteardown/pipeline/orchestrator.py`
- Test: `tests/pipeline/test_steps_strategy.py`

- [ ] **Step 1: 写失败测试**

`tests/pipeline/test_steps_strategy.py`:
```python
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline import steps
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.strategy.models import StrategyCard
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _fw():
    return Framework(id="hook-model", name="上瘾模型", category="habit", summary="s",
                     tags=["社交"],
                     principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
                     references=["r"])


def _profile():
    return ProductProfile(name="Demo", product_type="社交App", one_liner="x",
                          features=[Feature(name="动态", description="d", user_goal="g")],
                          touchpoints=[])


def _mapping():
    return Mapping(feature="动态", framework_id="hook-model", principle_id="trigger",
                   rationale="r", evidence="e", confidence=0.9)


def test_map_features_injects_strategy_guidance():
    provider = FakeProvider(structured_responses=[MappingList(mappings=[_mapping()])])
    steps.map_features(provider, _profile(), [_fw()],
                       strategy_guidance="- 社交产品优先社交证明")
    prompt = provider.calls[0]["prompt"]
    assert "社交产品优先社交证明" in prompt
    assert "供参考" in prompt


def test_assess_experience_injects_strategy_guidance():
    provider = FakeProvider(structured_responses=[ExperienceAssessment()])
    steps.assess_experience(provider, _profile(), [_mapping()],
                            strategy_guidance="- 订阅产品重点查退订暗黑模式")
    prompt = provider.calls[0]["prompt"]
    assert "订阅产品重点查退订暗黑模式" in prompt


def _queue():
    return [
        _profile(),                              # step1
        MappingList(mappings=[_mapping()]),      # step3
        ExperienceAssessment(),                  # step4
        Synthesis(executive_summary="总结"),     # step5
    ]


def test_run_teardown_dispatches_cards_to_right_steps():
    cards = [
        StrategyCard(id="m", rule="MAP规则", rationale="r", target_step="mapping"),
        StrategyCard(id="a", rule="ASSESS规则", rationale="r", target_step="assessment"),
    ]
    provider = FakeProvider(structured_responses=_queue())
    run_teardown(provider, "desc", library=[_fw()], generated_at="t", strategy_cards=cards)
    step1 = provider.calls[0]["prompt"]
    step3 = provider.calls[1]["prompt"]
    step4 = provider.calls[2]["prompt"]
    assert "MAP规则" not in step1 and "ASSESS规则" not in step1   # step1 不受影响
    assert "MAP规则" in step3 and "ASSESS规则" not in step3       # mapping 卡进 step3
    assert "ASSESS规则" in step4 and "MAP规则" not in step4       # assessment 卡进 step4


def test_run_teardown_none_matches_prior_behavior():
    provider = FakeProvider(structured_responses=_queue())
    result = run_teardown(provider, "desc", library=[_fw()], generated_at="t")
    assert result.executive_summary == "总结"
    assert "供参考的拆解策略" not in provider.calls[1]["prompt"]
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/pipeline/test_steps_strategy.py -v`
Expected: FAIL — `map_features() got an unexpected keyword argument 'strategy_guidance'`

- [ ] **Step 3a: 改 map_features(steps.py)**

把 `map_features` 的签名与 ref_block 段替换(保留其余循环体不变)。签名改为:
```python
def map_features(
    provider: LLMProvider,
    profile: ProductProfile,
    frameworks: list[Framework],
    prior_summary: str | None = None,
    strategy_guidance: str | None = None,
) -> list[Mapping]:
    """Step 3:逐功能/触点映射到框架原则。单项失败标 error 并继续。
    prior_summary=历史相似案例;strategy_guidance=历史归纳的拆解策略(均仅供参考)。"""
    brief = _frameworks_brief(frameworks)
    valid_ids = ", ".join(fw.id for fw in frameworks)
    ref_block = ""
    if prior_summary:
        ref_block = (
            "\n以下是仅供参考的历史相似案例,请独立判断当前产品,不要照搬:\n"
            f"{prior_summary}\n"
        )
    if strategy_guidance:
        ref_block += (
            "\n以下是历史归纳的拆解策略,供参考,请结合当前产品独立判断:\n"
            f"{strategy_guidance}\n"
        )
```

- [ ] **Step 3b: 改 assess_experience(steps.py)**

把 `assess_experience` 整个替换为:
```python
def assess_experience(
    provider: LLMProvider,
    profile: ProductProfile,
    mappings: list[Mapping],
    strategy_guidance: str | None = None,
) -> ExperienceAssessment:
    """Step 4:整体体验评估 + 暗黑模式/伦理标注。
    strategy_guidance=历史归纳的评估策略(仅供参考)。"""
    mapping_lines = "\n".join(
        f"- {m.feature}: {m.framework_id}.{m.principle_id} — {m.evidence}"
        for m in mappings
        if not m.error
    )
    guide = ""
    if strategy_guidance:
        guide = ("\n以下是历史归纳的拆解策略,供参考,请结合当前产品独立判断:\n"
                 f"{strategy_guidance}\n")
    prompt = (
        f"产品:{profile.name}({profile.one_liner})。\n"
        f"已识别的心理学机制:\n{mapping_lines}\n"
        f"{guide}\n"
        "请给出整体体验评估:优势、摩擦点、伦理/暗黑模式警示、机会点。"
    )
    return provider.structured_complete(prompt, ExperienceAssessment, system=_SYSTEM)
```

- [ ] **Step 3c: 改 run_teardown(orchestrator.py)**

顶部 import 追加:
```python
from psyteardown.strategy.models import StrategyCard
from psyteardown.strategy.select import select_for
```
把 `run_teardown` 签名的 `prior_summary` 行后加参数,并改 step3/step4 调用:
```python
    prior_summary: str | None = None,
    strategy_cards: list[StrategyCard] | None = None,
) -> TeardownResult:
    """跑完整流水线。generated_at 由调用方传入(脚本环境禁用 datetime.now)。
    prior_summary 注入 step3;strategy_cards 按 target_step 分发注入 step3/step4。"""
    profile = steps.parse_product(provider, description)
    frameworks = steps.retrieve(profile, library, top_n=top_n)
    map_guide = select_for(strategy_cards, profile, "mapping") if strategy_cards else None
    assess_guide = select_for(strategy_cards, profile, "assessment") if strategy_cards else None
    mappings = steps.map_features(provider, profile, frameworks,
                                  prior_summary=prior_summary,
                                  strategy_guidance=map_guide or None)
    assessment = steps.assess_experience(provider, profile, mappings,
                                         strategy_guidance=assess_guide or None)
    summary = steps.synthesize(provider, profile, mappings, assessment)
```
(其余 return 块不变。)

- [ ] **Step 4: 运行,确认 PASS(5 passed)+ 全量回归**

Run: `pytest tests/pipeline/ -q`
Expected: 全绿(含 v2 的 test_orchestrator_memory、v1 的 pipeline 测试)。

Run: `pytest -q`
Expected: 全绿,`2 skipped`。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/steps.py src/psyteardown/pipeline/orchestrator.py tests/pipeline/test_steps_strategy.py
git commit -m "feat: inject strategy guidance into step3/step4 (dispatched by target_step)"
```

---

## Task 7: CLI —— strategize / reflect / strategies / analyze --use-strategies

**Files:**
- Modify: `src/psyteardown/cli.py`
- Test: `tests/test_cli_strategy.py`

> strategy 根目录取 `--store` 父目录(同 v3 `_growth_store`)。沿用 `--provider` 隐藏开关。

- [ ] **Step 1: 写失败测试**

`tests/test_cli_strategy.py`:
```python
from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()


class _FakeLLM:
    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self._payload

    def complete(self, prompt, *, system=None):
        return ""


def _seed_cases(tmp_path, n=3):
    db = tmp_path / "cases.db"
    for i in range(n):
        src = tmp_path / f"p{i}.txt"
        src.write_text(f"社交产品{i}:动态推送点赞 {i}", encoding="utf-8")
        r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                                "--out", str(tmp_path / f"r{i}.md"),
                                "--provider", "fake", "--embed-provider", "fake"])
        assert r.exit_code == 0, r.stdout
    return db


def test_strategize_list_approve_then_analyze(tmp_path, monkeypatch):
    db = _seed_cases(tmp_path)
    import psyteardown.cli as cli
    from psyteardown.strategy.models import StrategyCard, CardList
    from psyteardown.memory.store import CaseStore

    ids = [c.case_id for c, _ in CaseStore(db).all()]
    card = StrategyCard(id="prefer-social-proof", rule="社交产品优先社交证明框架",
                        rationale="社交案例反复高置信", target_step="mapping",
                        applies_to=["社交"], source_case_ids=ids)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CardList(cards=[card])))

    r = runner.invoke(app, ["strategize", "--store", str(db), "--min-support", "1",
                            "--provider", "fake"])
    assert r.exit_code == 0, r.stdout

    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "prefer-social-proof" in r.stdout

    r = runner.invoke(app, ["strategies", "approve", "prefer-social-proof", "--store", str(db)])
    assert r.exit_code == 0, r.stdout

    # analyze --use-strategies 应把该策略注入 step3(fake LLM 不校验内容,仅确认跑通)
    src = tmp_path / "q.txt"
    src.write_text("社交产品:群组动态与点赞", encoding="utf-8")
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--use-strategies", "--out", str(tmp_path / "q.md"),
                            "--provider", "fake", "--embed-provider", "fake"])
    assert r.exit_code == 0, r.stdout


def test_reflect_creates_candidate(tmp_path, monkeypatch):
    db = tmp_path / "cases.db"      # reflect 不需要案例
    import psyteardown.cli as cli
    from psyteardown.strategy.models import StrategyCard, CardList

    card = StrategyCard(id="no-dark-unsub", rule="订阅产品查退订暗黑模式",
                        rationale="复盘", target_step="assessment", applies_to=["订阅"])
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CardList(cards=[card])))
    r = runner.invoke(app, ["reflect", "--note", "订阅产品记得查退订暗黑模式",
                            "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "no-dark-unsub" in r.stdout


def test_strategies_reject(tmp_path, monkeypatch):
    db = tmp_path / "cases.db"
    import psyteardown.cli as cli
    from psyteardown.strategy.models import StrategyCard, CardList

    card = StrategyCard(id="temp", rule="r", rationale="r", target_step="mapping")
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM(CardList(cards=[card])))
    runner.invoke(app, ["reflect", "--note", "note", "--store", str(db), "--provider", "fake"])
    r = runner.invoke(app, ["strategies", "reject", "temp", "--store", str(db)])
    assert r.exit_code == 0
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "temp" not in r.stdout
```

- [ ] **Step 2: 运行,确认 FAIL**

Run: `pytest tests/test_cli_strategy.py -v`
Expected: FAIL — 无 `strategize`/`reflect`/`strategies` 命令。

- [ ] **Step 3a: cli.py 顶部新增 imports**

```python
from psyteardown.strategy.store import StrategyStore
from psyteardown.strategy.proposer import propose_strategies
from psyteardown.strategy.distill import distill_from_note
```

- [ ] **Step 3b: 新增 strategies 子应用 + helper(在 candidates_app 定义之后)**

```python
strategies_app = typer.Typer(help="拆解策略卡:审阅/批准/驳回")
app.add_typer(strategies_app, name="strategies")


def _strategy_store(store: Path) -> StrategyStore:
    return StrategyStore(store.parent)
```

- [ ] **Step 3c: analyze 增 --use-strategies 并注入**

在 `analyze` 的参数列表(`embed_provider` 那行之后)加:
```python
    use_strategies: bool = typer.Option(False, "--use-strategies", help="注入已批准的拆解策略卡"),
```
在 `analyze` 里,构造 `run_teardown` 调用之前加载策略卡。找到:
```python
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = run_teardown(llm, text, library=library, generated_at=now,
                          prior_summary=prior_summary)
```
替换为:
```python
    strategy_cards = None
    if use_strategies:
        strategy_cards = _strategy_store(store).list_approved()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = run_teardown(llm, text, library=library, generated_at=now,
                          prior_summary=prior_summary, strategy_cards=strategy_cards)
```

- [ ] **Step 3d: 新增 strategize / reflect / strategies 命令(文件末尾)**

```python
@app.command()
def strategize(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    min_support: int = typer.Option(3, "--min-support", help="策略卡需的最少支撑案例数"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
):
    """从案例库跨案例归纳候选策略卡(待人工审批)。"""
    cases = [c for c, _ in CaseStore(store).all()]
    if not cases:
        typer.echo("案例库为空,先用 analyze 积累案例再 strategize。")
        return
    sstore = _strategy_store(store)
    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards = propose_strategies(llm, cases, created_at=now, min_support=min_support)
    for card in cards:
        sstore.save_candidate(card)
    typer.echo(f"提炼出 {len(cards)} 张候选策略卡(待审):"
               + ", ".join(c.id for c in cards))


@app.command()
def reflect(
    note: str = typer.Option(..., "--note", help="你的拆解复盘笔记"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
):
    """把自然语言复盘蒸馏成候选策略卡(待人工审批)。"""
    sstore = _strategy_store(store)
    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards = distill_from_note(llm, note, created_at=now)
    for card in cards:
        sstore.save_candidate(card)
    typer.echo(f"蒸馏出 {len(cards)} 张候选策略卡(待审):"
               + ", ".join(c.id for c in cards))


@strategies_app.command("list")
def strategies_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """列出待审策略卡。"""
    cards = _strategy_store(store).list_candidates()
    if not cards:
        typer.echo("无候选策略卡。")
        return
    for c in cards:
        typer.echo(f"{c.id}\t[{c.target_step}]\t{c.rule}")


@strategies_app.command("show")
def strategies_show(
    strategy_id: str = typer.Argument(..., help="策略卡 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """查看策略卡详情。"""
    c = _strategy_store(store).get_candidate(strategy_id)
    if c is None:
        typer.echo(f"候选不存在:{strategy_id}", err=True)
        raise typer.Exit(code=1)
    applies = ", ".join(c.applies_to) or "(通用)"
    typer.echo(f"# {c.id} [{c.target_step}] 适用:{applies}\n规则:{c.rule}\n")
    typer.echo(f"依据:{c.rationale}")
    typer.echo(f"支撑案例:{', '.join(c.source_case_ids) or '(人工复盘)'}")


@strategies_app.command("approve")
def strategies_approve(
    strategy_id: str = typer.Argument(..., help="策略卡 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """批准策略卡(此后 analyze --use-strategies 生效)。"""
    from psyteardown.strategy.store import StrategyError

    try:
        path = _strategy_store(store).approve(strategy_id)
    except StrategyError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已批准 {strategy_id} → {path}")


@strategies_app.command("reject")
def strategies_reject(
    strategy_id: str = typer.Argument(..., help="策略卡 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """驳回并删除策略卡。"""
    from psyteardown.strategy.store import StrategyError

    try:
        _strategy_store(store).reject(strategy_id)
    except StrategyError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已驳回 {strategy_id}")
```

- [ ] **Step 4: 运行,确认 PASS(3 passed)+ 全量回归**

Run: `pytest tests/test_cli_strategy.py -v`
Expected: 3 passed。

Run: `pytest -q`
Expected: 全绿,`2 skipped`。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/cli.py tests/test_cli_strategy.py
git commit -m "feat: add strategize/reflect/strategies CLI; analyze --use-strategies"
```

---

## Task 8: README + 全量回归

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README**

标题行改为 `# psyteardown — 心理驱动型产品拆解 Agent(v4)`。

在"用法"段的 `psyteardown candidates reject <id>` 行之后插入:
```markdown
    psyteardown strategize                                       # 从案例归纳候选策略卡(待审)
    psyteardown reflect --note "社交产品别漏社交证明"             # 复盘蒸馏成候选策略卡
    psyteardown strategies list                                  # 列候选策略卡
    psyteardown strategies show <id>                             # 看详情
    psyteardown strategies approve <id>                          # 批准
    psyteardown strategies reject <id>                           # 驳回
    psyteardown analyze --input product.txt --use-strategies     # 注入已批准策略卡(默认关)
```

在"架构"小节的 `growth` 行之后追加:
```markdown
- `strategy` — 程序性记忆:从案例/复盘归纳拆解策略卡,人工审批后按步骤注入拆解流程
```

- [ ] **Step 2: 全量回归**

Run: `pytest -q`
Expected: 全绿,`2 skipped`。报确切 `N passed, 2 skipped`。

- [ ] **Step 3: 手动跑通(fake,不触网)**

```bash
printf '社交健身App,打卡、排行榜、好友点赞、限时挑战' > /tmp/p.txt
psyteardown analyze --input /tmp/p.txt --store /tmp/c.db --out /tmp/r.md --provider fake --embed-provider fake
psyteardown analyze --input /tmp/p.txt --store /tmp/c.db --use-strategies --out /tmp/r2.md --provider fake --embed-provider fake
```
Expected: 两次都成功;第二次带 --use-strategies(无已批准卡时等价于普通 analyze,不报错)。

- [ ] **Step 4: 提交**

```bash
git add README.md
git commit -m "docs: document v4 strategize/reflect/strategies commands"
```

---

## 自检:spec 覆盖核对

- strategize 跨案例归纳候选 → Task 4 + Task 7 ✅
- reflect 复盘蒸馏(副入口,豁免 min_support) → Task 5 + Task 7 ✅
- 人工审批 list/show/approve/reject + 台账防复活 → Task 2 + Task 7 ✅
- StrategyCard(候选=已批准同构,含 applies_to/target_step/source) → Task 1 ✅
- target_step 分发注入(mapping→step3、assessment→step4、retrieval 并入 step3) → Task 3 + Task 6 ✅
- applies_to 品类命中(通配/子串) → Task 3 ✅
- analyze --use-strategies 默认关、注入文案防污染 → Task 6 + Task 7 ✅
- 向后兼容(strategy_cards=None = 既有行为) → Task 6 ✅
- 离线可测(全 Fake)、无新依赖 → 全任务 ✅
- id 净化防路径穿越 → Task 2 ✅
- YAGNI 不做项(自改写/自评/真改 step2) → 计划未涉及 ✅

**类型一致性核对**:`StrategyStore` 方法名(save_candidate/list_candidates/get_candidate/approve/reject/is_rejected/approved_dir/list_approved)在 Task 2 定义、Task 7 使用一致;`select_for(cards, profile, step)` 在 Task 3 定义、Task 6 使用一致;`_VALID_STEPS` 在 select.py 定义,proposer/distill 复用一致;`propose_strategies`/`distill_from_note` 的 `created_at` 关键字参数在 Task 4/5 定义、Task 7 使用一致。



