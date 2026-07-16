# v5 单案例自评(Self-Review)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拆解完成后系统对本次拆解做结构化批判自评(评分+亮点+缺陷+建议),存入案例、渲染进报告,并双通道接入 v4 策略学习闭环。

**Architecture:** 新建 `review/` 子系统(CaseReview 模型 + review_case 自评器);`Case` 加可选 `review` 字段(存进 case_json,零迁移);CLI 编排自评(pipeline 零改动);`strategize` 统计摘要带自评信号,`review --to-reflect` 复用 v4 `distill_from_note` 直达策略候选。

**Tech Stack:** Python 3.11+、Pydantic v2、Typer、SQLite、pytest(全部离线,FakeProvider)。

**Spec:** `docs/superpowers/specs/2026-07-16-v5-self-review-design.md`

**约定(全项目一致,勿违背):**
- 库核心不取当前时间——`reviewed_at` 由 CLI 注入。
- 测试绝不触网:LLM 用 `FakeProvider` 或 monkeypatch `_build_provider`;嵌入用 `--embed-provider fake`。
- 运行测试的命令都在仓库根 `D:\app\app-mental` 下执行。

---

### Task 1: CaseReview 模型

**Files:**
- Create: `src/psyteardown/review/__init__.py`
- Create: `src/psyteardown/review/models.py`
- Create: `tests/review/__init__.py`
- Test: `tests/review/test_models.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/review/__init__.py`(空文件)和 `tests/review/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from psyteardown.review.models import CaseReview


def test_defaults():
    r = CaseReview(score=0.7)
    assert r.strengths == []
    assert r.weaknesses == []
    assert r.suggestions == []
    assert r.reviewed_at == ""
    assert r.model == ""


def test_score_bounds_rejected():
    with pytest.raises(ValidationError):
        CaseReview(score=-0.1)
    with pytest.raises(ValidationError):
        CaseReview(score=1.1)


def test_json_roundtrip():
    r = CaseReview(score=0.6, strengths=["框架选得准"],
                   weaknesses=["社交证明置信虚高"],
                   suggestions=["先核对留存数据再定置信"],
                   reviewed_at="2026-07-16", model="fake")
    again = CaseReview.model_validate_json(r.model_dump_json())
    assert again.score == 0.6
    assert again.weaknesses == ["社交证明置信虚高"]
    assert again.reviewed_at == "2026-07-16"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/review/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.review'`

- [ ] **Step 3: 最小实现**

创建 `src/psyteardown/review/__init__.py`(空文件)和 `src/psyteardown/review/models.py`:

```python
"""单案例自评的数据模型(元认知第二块)。"""

from pydantic import BaseModel, Field


class CaseReview(BaseModel):
    score: float = Field(ge=0, le=1)                       # 0-1 总体质量分
    strengths: list[str] = Field(default_factory=list)     # 亮点:拆得好的地方
    weaknesses: list[str] = Field(default_factory=list)    # 缺陷:置信虚高/证据薄弱/疑似遗漏
    suggestions: list[str] = Field(default_factory=list)   # 改进建议(可喂 reflect 管道)
    reviewed_at: str = ""                                  # 调用方注入
    model: str = ""                                        # 自评用的模型标签
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/review/test_models.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/review tests/review
git commit -m "feat(review): CaseReview model for single-case self-critique"
```

---

### Task 2: Case 加可选 review 字段(旧数据兼容)

**Files:**
- Modify: `src/psyteardown/memory/models.py`
- Test: `tests/memory/test_models.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/memory/test_models.py` 末尾追加(该文件已有 Case 测试;若已有构造 TeardownResult 的 helper 则复用,否则加下面的自足 helper):

```python
from psyteardown.review.models import CaseReview
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _minimal_result():
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="App", one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=[], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def test_case_review_defaults_none():
    from psyteardown.memory.models import Case
    c = Case.from_result(_minimal_result(), description="d", created_at="t")
    assert c.review is None


def test_case_old_json_without_review_loads():
    """旧库的 case_json 没有 review 键 → 加载后 review 为 None(零迁移)。"""
    from psyteardown.memory.models import Case
    c = Case.from_result(_minimal_result(), description="d", created_at="t")
    data = c.model_dump()
    data.pop("review")                       # 模拟 v4 及以前的存量数据
    old = Case.model_validate(data)
    assert old.review is None


def test_case_review_roundtrip():
    from psyteardown.memory.models import Case
    c = Case.from_result(_minimal_result(), description="d", created_at="t")
    c.review = CaseReview(score=0.8, suggestions=["建议1"])
    again = Case.model_validate_json(c.model_dump_json())
    assert again.review is not None
    assert again.review.score == 0.8
    assert again.review.suggestions == ["建议1"]
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/memory/test_models.py -v`
Expected: 新增 3 个测试 FAIL — `Case` 无 `review` 字段(assignment 报 ValidationError 或 attribute 不存在)

- [ ] **Step 3: 最小实现**

修改 `src/psyteardown/memory/models.py`:

在 import 区加:

```python
from psyteardown.review.models import CaseReview
```

在 `Case` 的 `created_at: str            # 调用方注入` 一行后加字段:

```python
    review: CaseReview | None = None   # v5 单案例自评;旧数据自动 None
```

(`from_result` 不改——review 由 CLI 在自评后赋值。)

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/memory/ -v`
Expected: 全部 passed(含既有测试,确认无回归)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/memory/models.py tests/memory/test_models.py
git commit -m "feat(memory): optional Case.review field, zero-migration backward compat"
```

---

### Task 3: CaseStore.get_with_embedding

**Files:**
- Modify: `src/psyteardown/memory/store.py`
- Test: `tests/memory/test_store.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/memory/test_store.py` 末尾追加(该文件已有 save/get 测试与 Case 构造方式,沿用其已有 helper 构造 case;若无可用 helper,用 Task 2 的 `_minimal_result` 同款构造):

```python
def test_get_with_embedding_hit(tmp_path):
    from psyteardown.memory.store import CaseStore
    from psyteardown.memory.models import Case
    from psyteardown.pipeline.schemas import (
        ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
    )
    result = TeardownResult(
        product=ProductProfile(name="Demo", product_type="App", one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=[], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    case = Case.from_result(result, description="d", created_at="t")
    store = CaseStore(tmp_path / "cases.db")
    store.save(case, [0.1, 0.2, 0.3])

    hit = store.get_with_embedding(case.case_id)
    assert hit is not None
    got_case, vec = hit
    assert got_case.case_id == case.case_id
    assert len(vec) == 3
    assert abs(vec[1] - 0.2) < 1e-6           # float32 往返有精度损失


def test_get_with_embedding_missing(tmp_path):
    from psyteardown.memory.store import CaseStore
    store = CaseStore(tmp_path / "cases.db")
    assert store.get_with_embedding("nope") is None
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/memory/test_store.py -v`
Expected: 新增 2 个测试 FAIL — `AttributeError: 'CaseStore' object has no attribute 'get_with_embedding'`

- [ ] **Step 3: 最小实现**

在 `src/psyteardown/memory/store.py` 的 `get` 方法后加:

```python
    def get_with_embedding(self, case_id: str) -> tuple[Case, list[float]] | None:
        """按 id 取案例及其向量(供补评 upsert 回写);不存在 → None。"""
        row = self._conn.execute(
            "SELECT case_json, embedding FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        if row is None:
            return None
        case = Case.model_validate_json(row[0])
        vec = np.frombuffer(row[1], dtype=np.float32).tolist()
        return case, vec
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/memory/ -v`
Expected: 全部 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/memory/store.py tests/memory/test_store.py
git commit -m "feat(memory): CaseStore.get_with_embedding for re-review upsert"
```

---

### Task 4: 自评器 review_case

**Files:**
- Create: `src/psyteardown/review/critic.py`
- Test: `tests/review/test_critic.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/review/test_critic.py`:

```python
from psyteardown.llm.base import FakeProvider
from psyteardown.review.critic import review_case
from psyteardown.review.models import CaseReview
from psyteardown.pipeline.schemas import (
    ProductProfile, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result():
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="社交App", one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[
            Mapping(feature="动态", framework_id="hook-model", principle_id="trigger",
                    rationale="r", evidence="点赞红点", confidence=0.9),
            Mapping(feature="签到", framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error="解析失败"),
        ],
        assessment=ExperienceAssessment(strengths=["上手快"], friction_points=["通知多"]),
        executive_summary="总结",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def test_result_brief_reaches_prompt_and_stamps_meta():
    provider = FakeProvider(structured_responses=[CaseReview(score=0.6)])
    out = review_case(provider, _result(), reviewed_at="2026-07-16", model_label="m1")
    assert out.reviewed_at == "2026-07-16"
    assert out.model == "m1"
    prompt = provider.calls[0]["prompt"]
    assert "hook-model.trigger" in prompt          # 机制映射进 prompt
    assert "点赞红点" in prompt                     # 证据进 prompt
    assert "映射失败" in prompt                     # 失败 mapping 标注进 prompt
    assert "上手快" in prompt                       # 体验评估进 prompt
    assert provider.calls[0]["system"] is not None  # 批判性 system 立场


def test_model_label_defaults_empty():
    provider = FakeProvider(structured_responses=[CaseReview(score=0.5)])
    out = review_case(provider, _result(), reviewed_at="t")
    assert out.model == ""
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/review/test_critic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.review.critic'`

- [ ] **Step 3: 最小实现**

创建 `src/psyteardown/review/critic.py`:

```python
"""单案例自评:对一次拆解结果做批判性质量审阅(元认知)。"""

from psyteardown.llm.base import LLMProvider
from psyteardown.pipeline.schemas import TeardownResult
from psyteardown.review.models import CaseReview

_SYSTEM = (
    "你是产品心理学拆解的批判性审阅者,宁可挑剔不可捧场。"
    "缺陷必须指向具体 mapping 或具体遗漏(哪个框架/心理机制疑似漏拆);"
    "证据薄弱却给高置信的必须点名;不接受空泛表扬。"
)


def _result_brief(result: TeardownResult) -> str:
    p = result.product
    lines = [f"产品:{p.name}({p.product_type})— {p.one_liner}", "机制映射:"]
    for m in result.mappings:
        if m.error:
            lines.append(f"- {m.feature}:映射失败({m.error})")
        else:
            lines.append(
                f"- {m.feature} → {m.framework_id}.{m.principle_id}"
                f"(置信{m.confidence:.1f});证据:{m.evidence}"
            )
    a = result.assessment
    lines.append(
        f"体验评估:优势={'; '.join(a.strengths) or '—'};"
        f"摩擦={'; '.join(a.friction_points) or '—'}"
    )
    lines.append(f"执行摘要:{result.executive_summary}")
    return "\n".join(lines)


def review_case(
    provider: LLMProvider,
    result: TeardownResult,
    *,
    reviewed_at: str,
    model_label: str = "",
) -> CaseReview:
    """单次 LLM 调用做批判自评;reviewed_at/model 由本函数注入返回值。"""
    prompt = (
        "以下是一次产品心理学拆解的完整结果,请做批判性自评:\n"
        f"{_result_brief(result)}\n\n"
        "请给出:score(0-1 总体质量分)、strengths(拆得好的地方)、"
        "weaknesses(缺陷:置信虚高/证据薄弱/疑似漏拆的框架或心理机制,须指向具体条目)、"
        "suggestions(下次怎么拆得更好的可操作建议)。"
    )
    review = provider.structured_complete(prompt, CaseReview, system=_SYSTEM)
    review.reviewed_at = reviewed_at
    review.model = model_label
    return review
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/review/ -v`
Expected: 全部 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/review/critic.py tests/review/test_critic.py
git commit -m "feat(review): review_case critic — structured self-critique of a teardown"
```

---

### Task 5: 通道① — strategize 统计摘要带自评信号

**Files:**
- Modify: `src/psyteardown/strategy/proposer.py`(`_case_brief` 函数)
- Test: `tests/strategy/test_proposer.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/strategy/test_proposer.py` 末尾追加(复用该文件已有的 `_case` helper):

```python
def test_case_brief_includes_review_signal():
    from psyteardown.review.models import CaseReview
    cases = [_case(str(i)) for i in range(3)]
    cases[0].review = CaseReview(score=0.6,
                                 weaknesses=["社交证明置信虚高"],
                                 suggestions=["先核对留存数据"])
    card = _card("prefer-x", ["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    propose_strategies(provider, cases, created_at="t", min_support=3)
    prompt = provider.calls[0]["prompt"]
    assert "自评 0.6" in prompt
    assert "社交证明置信虚高" in prompt
    assert "先核对留存数据" in prompt


def test_case_brief_without_review_unchanged():
    cases = [_case(str(i)) for i in range(3)]
    card = _card("prefer-x", ["0", "1", "2"])
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    propose_strategies(provider, cases, created_at="t", min_support=3)
    assert "自评" not in provider.calls[0]["prompt"]
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/strategy/test_proposer.py -v`
Expected: `test_case_brief_includes_review_signal` FAIL(prompt 中无"自评");`test_case_brief_without_review_unchanged` PASS(现状即无)

- [ ] **Step 3: 最小实现**

修改 `src/psyteardown/strategy/proposer.py` 的 `_case_brief`,整函数替换为:

```python
def _case_brief(cases: list[Case]) -> str:
    lines = []
    for c in cases:
        mech = "; ".join(
            f"{m.framework_id}.{m.principle_id}(置信{m.confidence:.1f}"
            + (",失败" if m.error else "") + ")"
            for m in c.result.mappings
        )
        line = f"- [{c.case_id}] {c.product_name}({c.result.product.product_type}):{mech}"
        if c.review is not None:
            line += (
                f"\n  自评 {c.review.score:.1f}:"
                f"缺陷={'; '.join(c.review.weaknesses) or '—'}; "
                f"建议={'; '.join(c.review.suggestions) or '—'}"
            )
        lines.append(line)
    return "\n".join(lines)
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/strategy/ -v`
Expected: 全部 passed(含既有测试,确认向后兼容)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/strategy/proposer.py tests/strategy/test_proposer.py
git commit -m "feat(strategy): case brief carries self-review signal into strategize"
```

---

### Task 6: 报告渲染自评节

**Files:**
- Modify: `src/psyteardown/report/render.py`
- Test: `tests/report/test_render.py`(追加)

- [ ] **Step 1: 写失败测试**

在 `tests/report/test_render.py` 末尾追加(复用该文件已有的 result 构造 helper;若无,用下面自足 helper):

```python
import json as _json

from psyteardown.review.models import CaseReview


def _result_for_review():
    from psyteardown.pipeline.schemas import (
        ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
    )
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="App", one_liner="x",
                               features=[], touchpoints=[]),
        frameworks_used=[], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def test_markdown_renders_review_section():
    review = CaseReview(score=0.65, strengths=["框架选得准"],
                        weaknesses=["证据薄弱"], suggestions=["补充数据"])
    md = render_markdown(_result_for_review(), review=review)
    assert "## 拆解自评" in md
    assert "0.65" in md
    assert "框架选得准" in md
    assert "证据薄弱" in md
    assert "补充数据" in md


def test_markdown_without_review_unchanged():
    result = _result_for_review()
    assert render_markdown(result) == render_markdown(result, review=None)
    assert "拆解自评" not in render_markdown(result)


def test_json_with_review_adds_top_level_key():
    review = CaseReview(score=0.65)
    payload = _json.loads(render_json(_result_for_review(), review=review))
    assert payload["review"]["score"] == 0.65


def test_json_without_review_no_key():
    payload = _json.loads(render_json(_result_for_review()))
    assert "review" not in payload
```

注意:该文件顶部已有 `from psyteardown.report.render import render_json, render_markdown`(如无则补)。

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/report/test_render.py -v`
Expected: `test_markdown_renders_review_section` 与 `test_json_with_review_adds_top_level_key` FAIL — `render_markdown() got an unexpected keyword argument 'review'`

- [ ] **Step 3: 最小实现**

修改 `src/psyteardown/report/render.py`:

顶部 import 区改为:

```python
"""把 TeardownResult 渲染成 Markdown 或 JSON。"""

import json

from psyteardown.pipeline.schemas import TeardownResult
from psyteardown.review.models import CaseReview
```

`render_json` 整函数替换:

```python
def render_json(result: TeardownResult, *, review: CaseReview | None = None) -> str:
    if review is None:
        return result.model_dump_json(indent=2)
    payload = result.model_dump()
    payload["review"] = review.model_dump()
    return json.dumps(payload, ensure_ascii=False, indent=2)
```

`render_markdown` 签名改为:

```python
def render_markdown(result: TeardownResult, *, review: CaseReview | None = None) -> str:
```

并在「# 6. 机会点」段落之后、「# 7. 附录」段落之前插入:

```python
    # 6.5 拆解自评(v5,可选)
    if review is not None:
        out.append("## 拆解自评\n")
        out.append(f"- 总体评分:{review.score:.2f}")
        out.append(f"- 亮点:{_join(review.strengths)}")
        out.append(f"- 缺陷:{_join(review.weaknesses)}")
        out.append(f"- 改进建议:{_join(review.suggestions)}")
        out.append("")
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/report/ -v`
Expected: 全部 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/report/render.py tests/report/test_render.py
git commit -m "feat(report): optional self-review section in markdown/json output"
```

---

### Task 7: CLI — analyze --self-review(含 graceful 降级)

**Files:**
- Modify: `src/psyteardown/cli.py`
- Test: `tests/test_cli_review.py`(新建,前半部分)

- [ ] **Step 1: 写失败测试**

创建 `tests/test_cli_review.py`:

```python
from typer.testing import CliRunner

from psyteardown.cli import app
from psyteardown.memory.store import CaseStore

runner = CliRunner()


def _analyze(tmp_path, *extra):
    src = tmp_path / "p.txt"
    src.write_text("社交产品:动态推送点赞", encoding="utf-8")
    db = tmp_path / "cases.db"
    out = tmp_path / "r.md"
    r = runner.invoke(app, ["analyze", "--input", str(src), "--store", str(db),
                            "--out", str(out),
                            "--provider", "fake", "--embed-provider", "fake",
                            *extra])
    return r, db, out


def test_analyze_self_review_renders_and_saves(tmp_path):
    r, db, out = _analyze(tmp_path, "--self-review")
    assert r.exit_code == 0, r.stdout
    assert "拆解自评" in out.read_text(encoding="utf-8")
    cases = [c for c, _ in CaseStore(db).all()]
    assert len(cases) == 1
    assert cases[0].review is not None


def test_analyze_self_review_no_save_still_renders(tmp_path):
    r, db, out = _analyze(tmp_path, "--self-review", "--no-save")
    assert r.exit_code == 0, r.stdout
    assert "拆解自评" in out.read_text(encoding="utf-8")
    assert CaseStore(db).count() == 0


def test_analyze_without_flag_no_review(tmp_path):
    r, db, out = _analyze(tmp_path)
    assert r.exit_code == 0, r.stdout
    assert "拆解自评" not in out.read_text(encoding="utf-8")
    cases = [c for c, _ in CaseStore(db).all()]
    assert cases[0].review is None


def test_analyze_self_review_failure_degrades(tmp_path, monkeypatch):
    import psyteardown.cli as cli

    def _boom(*a, **k):
        raise RuntimeError("自评炸了")

    monkeypatch.setattr(cli, "review_case", _boom)
    r, db, out = _analyze(tmp_path, "--self-review")
    assert r.exit_code == 0, r.stdout          # 降级不中断
    text = out.read_text(encoding="utf-8")
    assert "拆解自评" not in text               # 报告无自评节但照常产出
    cases = [c for c, _ in CaseStore(db).all()]
    assert len(cases) == 1                      # 案例照常落盘(review=None)
    assert cases[0].review is None
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_cli_review.py -v`
Expected: FAIL — `analyze` 无 `--self-review` 选项(typer 报 "No such option");降级测试报 cli 无 `review_case` 属性

- [ ] **Step 3: 实现**

修改 `src/psyteardown/cli.py`,共 4 处:

**(a)** import 区加两行(放在 `from psyteardown.report.render import ...` 之后):

```python
from psyteardown.review.critic import review_case
from psyteardown.review.models import CaseReview
```

**(b)** `_build_provider` 的 fake 队列末尾追加第 4 项(analyze --self-review 消费;不开自评时留队列无害):

```python
        return FakeProvider(structured_responses=[
            ProductProfile(name="样例产品", product_type="App",
                           one_liner="自动生成的占位画像", features=[], touchpoints=[]),
            ExperienceAssessment(),
            Synthesis(executive_summary="(fake provider 占位摘要)"),
            CaseReview(score=0.5, suggestions=["(fake) 占位改进建议"]),
        ])
```

**(c)** `analyze` 签名在 `use_strategies` 参数后加:

```python
    self_review: bool = typer.Option(False, "--self-review",
                                     help="拆解后追加一次 LLM 自评(默认关)"),
```

**(d)** `analyze` 函数体:在 `result = run_teardown(...)` 之后、`rendered = ...` 之前插入:

```python
    # 自评是增强:失败降级,不拖垮报告(与记忆功能同风格)。
    review_obj: CaseReview | None = None
    if self_review:
        try:
            review_obj = review_case(llm, result, reviewed_at=now,
                                     model_label=result.meta.model)
        except Exception as e:  # noqa: BLE001
            typer.echo(f"提示:自评失败({e}),报告不含自评节。", err=True)
```

`rendered` 一行改为:

```python
    rendered = (render_json(result, review=review_obj) if fmt == "json"
                else render_markdown(result, review=review_obj))
```

落盘块中 `case = Case.from_result(...)` 之后、`case_store.save(...)` 之前插一行:

```python
            case.review = review_obj
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_cli_review.py tests/test_cli.py tests/test_cli_memory.py -v`
Expected: 全部 passed(既有 analyze 测试无回归)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/cli.py tests/test_cli_review.py
git commit -m "feat(cli): analyze --self-review with graceful degradation"
```

---

### Task 8: CLI — review 命令(补评 + --to-reflect)

**Files:**
- Modify: `src/psyteardown/cli.py`
- Test: `tests/test_cli_review.py`(追加后半部分)

- [ ] **Step 1: 写失败测试**

在 `tests/test_cli_review.py` 末尾追加:

```python
class _FakeLLM:
    """按队列返回预置结构化结果(monkeypatch _build_provider 用)。"""

    def __init__(self, payloads):
        self._p = list(payloads)
        self.calls = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        return self._p.pop(0)

    def complete(self, prompt, *, system=None):
        return ""


def _seed_case(tmp_path):
    """无自评落盘一个案例,返回 (db, case_id)。"""
    r, db, _ = _analyze(tmp_path)
    assert r.exit_code == 0, r.stdout
    cases = [c for c, _ in CaseStore(db).all()]
    return db, cases[0].case_id


def test_review_backfills_and_overwrites(tmp_path, monkeypatch):
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview

    db, cid = _seed_case(tmp_path)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.4)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert CaseStore(db).get(cid).review.score == 0.4

    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.9)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert CaseStore(db).get(cid).review.score == 0.9      # 覆盖旧自评


def test_review_missing_case_errors(tmp_path):
    db = tmp_path / "cases.db"
    r = runner.invoke(app, ["review", "nope", "--store", str(db), "--provider", "fake"])
    assert r.exit_code == 1


def test_review_to_reflect_creates_strategy_candidate(tmp_path, monkeypatch):
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview
    from psyteardown.strategy.models import StrategyCard, CardList

    db, cid = _seed_case(tmp_path)
    card = StrategyCard(id="check-retention-first", rule="定置信前先核对留存数据",
                        rationale="自评建议", target_step="mapping")
    monkeypatch.setattr(cli, "_build_provider", lambda name: _FakeLLM([
        CaseReview(score=0.6, suggestions=["先核对留存数据再定置信"]),
        CardList(cards=[card]),
    ]))
    r = runner.invoke(app, ["review", cid, "--store", str(db),
                            "--to-reflect", "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "check-retention-first" in r.stdout


def test_review_to_reflect_empty_suggestions_skips(tmp_path, monkeypatch):
    import psyteardown.cli as cli
    from psyteardown.review.models import CaseReview

    db, cid = _seed_case(tmp_path)
    monkeypatch.setattr(cli, "_build_provider",
                        lambda name: _FakeLLM([CaseReview(score=0.9)]))
    r = runner.invoke(app, ["review", cid, "--store", str(db),
                            "--to-reflect", "--provider", "fake"])
    assert r.exit_code == 0, r.stdout
    assert "跳过" in r.stdout
    r = runner.invoke(app, ["strategies", "list", "--store", str(db)])
    assert "无候选策略卡" in r.stdout
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/test_cli_review.py -v`
Expected: 新增测试 FAIL — typer 报无 `review` 命令(exit_code == 2 而非 0/1)

- [ ] **Step 3: 实现**

在 `src/psyteardown/cli.py` 的 `analyze` 命令之后加顶层命令:

```python
@app.command()
def review(
    case_id: str = typer.Argument(..., help="案例 id(见 analyze 落盘输出)"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    to_reflect: bool = typer.Option(False, "--to-reflect",
                                    help="把自评改进建议蒸馏成候选策略卡(待人工审批)"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
):
    """对历史案例补做批判自评(覆盖旧自评);可选直达策略蒸馏管道。"""
    case_store = CaseStore(store)
    hit = case_store.get_with_embedding(case_id)
    if hit is None:
        typer.echo(f"案例不存在:{case_id}", err=True)
        raise typer.Exit(code=1)
    case, emb = hit

    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 用户显式要求自评:失败直接报错,不静默(与 analyze 内降级不同)。
    rev = review_case(llm, case.result, reviewed_at=now,
                      model_label=case.result.meta.model)
    case.review = rev
    case_store.save(case, emb)

    typer.echo(f"自评完成:{case_id} 总体评分 {rev.score:.2f}")
    for w in rev.weaknesses:
        typer.echo(f"- 缺陷:{w}")
    for s in rev.suggestions:
        typer.echo(f"- 建议:{s}")

    if to_reflect:
        if not rev.suggestions:
            typer.echo("无改进建议,跳过策略蒸馏。")
            return
        note = (f"对案例「{case.product_name}」拆解的自评改进建议:\n"
                + "\n".join(f"- {s}" for s in rev.suggestions))
        cards = distill_from_note(llm, note, created_at=now)
        sstore = _strategy_store(store)
        for card in cards:
            sstore.save_candidate(card)
        typer.echo(f"蒸馏出 {len(cards)} 张候选策略卡(待审):"
                   + ", ".join(c.id for c in cards))
```

(`distill_from_note`、`_strategy_store`、`CaseStore` 均已在文件顶部 import,无需新增。)

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/test_cli_review.py -v`
Expected: 全部 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/cli.py tests/test_cli_review.py
git commit -m "feat(cli): review command — backfill self-critique, --to-reflect to strategy pipeline"
```

---

### Task 9: 文档、全量回归、收尾

**Files:**
- Modify: `README.md`
- Modify: `src/psyteardown/cli.py:26`(Typer help 版本号)

- [ ] **Step 1: 更新 README**

`README.md` 三处:

1. 标题行 `# psyteardown — 心理驱动型产品拆解 Agent(v4)` → `(v5)`;首段末尾补一句:`v5 元认知自评(单案例自评 + 策略闭环)。`
2. 用法段在 `psyteardown analyze --input product.txt --use-strategies` 行后加:

```
    psyteardown analyze --input product.txt --self-review         # 拆解后追加 LLM 自评(默认关)
    psyteardown review <case_id>                                  # 历史案例补评(覆盖旧自评)
    psyteardown review <case_id> --to-reflect                     # 补评 + 建议直达策略候选
```

3. 架构列表加一行(`strategy` 行之后):

```
- `review` — 元认知自评:拆解后批判性质量自评,信号回流 strategize / reflect
```

- [ ] **Step 2: 更新 CLI help 版本号**

`src/psyteardown/cli.py` 第 26 行:

```python
app = typer.Typer(help="心理驱动型产品拆解 Agent(v5)")
```

- [ ] **Step 3: 全量回归**

Run: `python -m pytest`
Expected: 约 150 passed / 2 skipped(v4 基线 131 passed / 2 skipped + 本计划新增 ~19 个),0 failed

- [ ] **Step 4: 提交**

```bash
git add README.md src/psyteardown/cli.py
git commit -m "docs: document v5 self-review commands; bump CLI help to v5"
```

---

## 计划自审(已执行)

- **Spec 覆盖**:成功标准 1(Task 7)、2(Task 8)、3(Task 1+4)、4 双通道(Task 5 + Task 8)、5 pipeline 零改动(无任务碰 pipeline/ ✓)+ 全离线(所有测试 Fake ✓)。存储零迁移(Task 2)、get_with_embedding(Task 3)、报告渲染(Task 6)、README(Task 9)。
- **占位符扫描**:无 TBD/TODO;每个代码步骤均含完整代码。
- **类型一致性**:`CaseReview(score, strengths, weaknesses, suggestions, reviewed_at, model)` 全计划一致;`review_case(provider, result, *, reviewed_at, model_label="")` 在 Task 4/7/8 签名一致;`get_with_embedding(case_id) -> tuple[Case, list[float]] | None` 在 Task 3/8 一致;`render_*(result, *, review=None)` 在 Task 6/7 一致。
- **执行顺序依赖**:Task 2 依赖 Task 1(import CaseReview);Task 7 依赖 Task 1/4/6;Task 8 依赖 Task 3/7。按序执行即可。
