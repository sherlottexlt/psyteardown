# v6 MCP Server(交付层)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 v1–v5 内核封装为 stdio MCP server(6 个工具),Claude Code/Desktop 对话中直接调用;同时提取 CLI analyze 编排为共享函数。

**Architecture:** 新增 `mcp_server/` 交付层:`tools.py`(6 个工具纯函数 + CLI/MCP 共享编排 `analyze_product`,零 mcp 依赖,离线可测)+ `server.py`(FastMCP 装配,环境变量→依赖,零业务逻辑)。CLI `analyze` 改调共享编排,行为逐字节一致,以既有 CLI 测试全绿为回归锁。

**Tech Stack:** Python 3.11+、官方 `mcp` SDK(FastMCP + stdio)、Pydantic v2、pytest(工具测试全离线;server 测试 `importorskip("mcp")`)。

**Spec:** `docs/superpowers/specs/2026-07-17-v6-mcp-server-design.md`

**约定:**
- `tools.py` 绝不 import `mcp` 包(离线可测);`mcp` 只在 `server.py` 内部 import。
- 所有警告/提示文案与现有 CLI **逐字节相同**(回归锁依赖此)。
- 运行测试都在仓库根 `D:\app\app-mental`;当前基线 **175 passed / 2 skipped**。

---

### Task 1: 依赖与骨架

**Files:**
- Modify: `pyproject.toml`
- Create: `src/psyteardown/mcp_server/__init__.py`(空)
- Create: `tests/mcp_server/__init__.py`(空)

- [ ] **Step 1: 修改 pyproject.toml**

`[project.optional-dependencies]` 改为:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
embed = ["sentence-transformers>=2.2"]
mcp = ["mcp>=1.2"]
```

`[project.scripts]` 改为:

```toml
[project.scripts]
psyteardown = "psyteardown.cli:app"
psyteardown-mcp = "psyteardown.mcp_server.server:main"
```

- [ ] **Step 2: 创建空包文件**

创建 `src/psyteardown/mcp_server/__init__.py` 和 `tests/mcp_server/__init__.py`(均空文件)。

- [ ] **Step 3: 重装并验证**

Run: `pip install -e ".[dev,mcp]" 2>&1 | tail -2 && python -c "import mcp; import psyteardown.mcp_server; print('ok')"`
Expected: `ok`。若 mcp 安装因网络失败:报告 BLOCKED,勿绕过(镜像源已配置过 pip,通常可装)。

Run: `python -m pytest 2>&1 | tail -1`
Expected: 175 passed, 2 skipped(无回归)

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml src/psyteardown/mcp_server/__init__.py tests/mcp_server/__init__.py
git commit -m "chore: mcp extra + psyteardown-mcp entry point + mcp_server package skeleton"
```

---

### Task 2: 共享编排 analyze_product(CLI 改造 + 回归锁)

**Files:**
- Create: `src/psyteardown/mcp_server/tools.py`
- Modify: `src/psyteardown/cli.py`(import 区、删除 `_build_provider`/`_build_embed_provider` 本地定义、重写 `analyze` 函数体)
- Test: `tests/mcp_server/test_tools.py`(新建)

- [ ] **Step 1: 写失败测试**

创建 `tests/mcp_server/test_tools.py`:

```python
"""mcp_server.tools 单测:全离线(FakeProvider / FakeEmbeddingProvider)。"""

from pathlib import Path

from psyteardown.embed.base import FakeEmbeddingProvider
from psyteardown.mcp_server.tools import (
    AnalyzeOutcome, analyze_product, build_llm_provider,
)


def _fake_llm():
    return build_llm_provider("fake")


def _fake_embed_factory():
    return FakeEmbeddingProvider()


def test_analyze_product_returns_outcome(tmp_path):
    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="2026-07-17 12:00",
                        embed_factory=_fake_embed_factory)
    assert isinstance(o, AnalyzeOutcome)
    assert "# 心理学拆解报告" in o.rendered
    assert o.case_id is not None
    assert o.warnings == []


def test_analyze_product_no_save(tmp_path):
    from psyteardown.memory.store import CaseStore
    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="t", embed_factory=_fake_embed_factory,
                        no_save=True)
    assert o.case_id is None
    assert CaseStore(store).count() == 0


def test_analyze_product_embed_failure_degrades(tmp_path):
    def _boom():
        raise OSError("offline: 无法加载模型")

    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="t", embed_factory=_boom)
    assert "# 心理学拆解报告" in o.rendered          # 报告照常产出
    assert o.case_id is None                          # 未落盘
    assert any("记忆功能不可用" in w for w in o.warnings)


def test_analyze_product_self_review(tmp_path):
    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="t", embed_factory=_fake_embed_factory,
                        self_review=True)
    assert "拆解自评" in o.rendered
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/mcp_server/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError`(tools 模块不存在)

- [ ] **Step 3: 实现 tools.py(第一部分:builders + 共享编排)**

创建 `src/psyteardown/mcp_server/tools.py`:

```python
"""MCP 工具纯函数 + CLI/MCP 共享编排。零 mcp 依赖,离线可测。"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from psyteardown.embed.base import EmbeddingProvider, FakeEmbeddingProvider
from psyteardown.growth.store import GrowthStore
from psyteardown.kb.loader import load_frameworks
from psyteardown.llm.base import FakeProvider, LLMProvider
from psyteardown.memory.models import Case
from psyteardown.memory.retrieval import search_similar, summarize_cases
from psyteardown.memory.store import CaseStore
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.pipeline.schemas import (
    ExperienceAssessment, ProductProfile, Synthesis,
)
from psyteardown.report.render import render_json, render_markdown
from psyteardown.review.critic import review_case
from psyteardown.review.models import CaseReview
from psyteardown.strategy.store import StrategyStore

DEFAULT_STORE = Path(".psyteardown/cases.db")


def build_llm_provider(name: str) -> LLMProvider:
    if name == "fake":
        return FakeProvider(structured_responses=[
            ProductProfile(name="样例产品", product_type="App",
                           one_liner="自动生成的占位画像", features=[], touchpoints=[]),
            ExperienceAssessment(),
            Synthesis(executive_summary="(fake provider 占位摘要)"),
            CaseReview(score=0.5, suggestions=["(fake) 占位改进建议"]),
        ])
    if name == "deepseek":
        from psyteardown.llm.deepseek import DeepSeekProvider

        return DeepSeekProvider()
    from psyteardown.llm.claude import ClaudeProvider

    return ClaudeProvider()


def build_embed_provider(name: str) -> EmbeddingProvider:
    if name == "fake":
        return FakeEmbeddingProvider()
    if name == "ollama":
        from psyteardown.embed.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider()
    from psyteardown.embed.local import LocalEmbeddingProvider

    return LocalEmbeddingProvider()


@dataclass
class AnalyzeOutcome:
    rendered: str                  # 渲染好的报告(md 或 json)
    case_id: str | None            # 落盘成功时的案例 id;未落盘 → None
    warnings: list[str] = field(default_factory=list)   # 降级提示(与 CLI 文案一致)


def analyze_product(
    llm: LLMProvider,
    description: str,
    *,
    store: Path,
    now: str,
    embed_factory: Callable[[], EmbeddingProvider],
    use_memory: bool = False,
    no_save: bool = False,
    use_strategies: bool = False,
    self_review: bool = False,
    fmt: str = "md",
) -> AnalyzeOutcome:
    """CLI analyze 与 MCP teardown 的共享编排。description 须非空(调用方校验)。

    警告不打印,收集进 warnings 由调用方决定呈现方式;文案与 v5 CLI 逐字一致。
    """
    warnings: list[str] = []
    library = load_frameworks(learned_dir=GrowthStore(store.parent).learned_dir())

    # 记忆是增强,不应让其失败(如离线无嵌入模型)拖垮核心拆解。
    emb: EmbeddingProvider | None = None
    case_store: CaseStore | None = None
    if use_memory or not no_save:
        try:
            emb = embed_factory()
            case_store = CaseStore(store)
        except Exception as e:  # noqa: BLE001 — 记忆不可用时降级,不中断拆解
            warnings.append(f"提示:记忆功能不可用({e}),本次跳过案例库。")
            emb = case_store = None

    prior_summary: str | None = None
    if use_memory and case_store is not None and emb is not None:
        try:
            hits = search_similar(case_store, emb, description, top_k=3)
            prior_summary = summarize_cases([c for c, _ in hits]) or None
        except Exception as e:  # noqa: BLE001
            warnings.append(f"提示:相似案例检索失败({e}),本次不注入历史参考。")

    strategy_cards = None
    if use_strategies:
        strategy_cards = StrategyStore(store.parent).list_approved()

    result = run_teardown(llm, description, library=library, generated_at=now,
                          prior_summary=prior_summary, strategy_cards=strategy_cards)

    # 自评是增强:失败降级,不拖垮报告(与记忆功能同风格)。
    review_obj: CaseReview | None = None
    if self_review:
        try:
            review_obj = review_case(llm, result, reviewed_at=now,
                                     model_label=result.meta.model)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"提示:自评失败({e}),报告不含自评节。")

    rendered = (render_json(result, review=review_obj) if fmt == "json"
                else render_markdown(result, review=review_obj))

    case_id: str | None = None
    if not no_save and case_store is not None and emb is not None:
        try:
            case = Case.from_result(result, description=description, created_at=now)
            case.review = review_obj
            if review_obj is None:
                old = case_store.get(case.case_id)
                if old is not None and old.review is not None:
                    warnings.append(
                        "提示:同描述旧案例含自评,本次未开自评,旧自评将被覆盖丢弃。")
            case_store.save(case, emb.embed([description])[0])
            case_id = case.case_id
        except Exception as e:  # noqa: BLE001
            warnings.append(f"提示:案例落盘失败({e}),报告已照常产出。")

    return AnalyzeOutcome(rendered=rendered, case_id=case_id, warnings=warnings)
```

- [ ] **Step 4: 运行新测试确认通过**

Run: `python -m pytest tests/mcp_server/test_tools.py -v`
Expected: 4 passed

- [ ] **Step 5: CLI 改造(改调共享函数)**

修改 `src/psyteardown/cli.py`:

**(a)** 删除本地 `_build_provider`、`_build_embed_provider` 两个函数定义(cli.py:49-76),以及因此不再被 cli.py 使用的 import(`FakeProvider`、`FakeEmbeddingProvider`、`ProductProfile`、`ExperienceAssessment`、`Synthesis`、`run_teardown`、`render_json`、`render_markdown`、`Case`、`summarize_cases`——注意 `search_similar`、`CaseStore`、`review_case`、`CaseReview`、`load_frameworks`、`LLMProvider`、`EmbeddingProvider` 等仍被其他命令使用,须保留;逐个确认后再删)。加:

```python
from psyteardown.mcp_server.tools import (
    analyze_product,
    build_embed_provider as _build_embed_provider,
    build_llm_provider as _build_provider,
)
```

(别名保证既有测试的 `monkeypatch.setattr(cli, "_build_provider", ...)` 与 `from psyteardown.cli import _build_embed_provider` 继续生效。)

**(b)** `analyze` 命令签名不变,函数体整体替换为:

```python
    """拆解一个产品描述,输出结构化报告;默认落盘为案例。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)

    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    outcome = analyze_product(
        llm, text, store=store, now=now,
        embed_factory=lambda: _build_embed_provider(embed_provider),
        use_memory=use_memory, no_save=no_save,
        use_strategies=use_strategies, self_review=self_review, fmt=fmt,
    )
    for w in outcome.warnings:
        typer.echo(w, err=True)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(outcome.rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(outcome.rendered)
    if outcome.case_id:
        typer.echo(f"已落盘案例 {outcome.case_id}")
```

- [ ] **Step 6: 回归锁——全量测试**

Run: `python -m pytest 2>&1 | tail -1`
Expected: **179 passed, 2 skipped**(175 基线 + 本任务 4 新增),0 failed。任何 CLI 测试失败 = 提取改变了行为,必须修到全绿,不许改动既有测试文件。

- [ ] **Step 7: 提交**

```bash
git add src/psyteardown/mcp_server/tools.py src/psyteardown/cli.py tests/mcp_server/test_tools.py
git commit -m "refactor: extract shared analyze orchestration to mcp_server.tools; CLI delegates"
```

---

### Task 3: teardown_tool

**Files:**
- Modify: `src/psyteardown/mcp_server/tools.py`(追加)
- Test: `tests/mcp_server/test_tools.py`(追加)

- [ ] **Step 1: 写失败测试** — 在 `tests/mcp_server/test_tools.py` 末尾追加:

```python
def test_teardown_tool_happy_path(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool
    store = tmp_path / "cases.db"
    out = teardown_tool("社交产品:动态推送点赞", store=store,
                        llm=_fake_llm(), embed_factory=_fake_embed_factory)
    assert "# 心理学拆解报告" in out
    assert "已落盘案例" in out


def test_teardown_tool_empty_description(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool
    out = teardown_tool("   ", store=tmp_path / "cases.db",
                        llm=_fake_llm(), embed_factory=_fake_embed_factory)
    assert out == "错误:输入为空。"


def test_teardown_tool_self_review(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool
    out = teardown_tool("社交产品:动态推送点赞", store=tmp_path / "cases.db",
                        llm=_fake_llm(), embed_factory=_fake_embed_factory,
                        self_review=True)
    assert "拆解自评" in out


def test_teardown_tool_degrades_with_warning_in_text(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool

    def _boom():
        raise OSError("offline")

    out = teardown_tool("社交产品:动态推送点赞", store=tmp_path / "cases.db",
                        llm=_fake_llm(), embed_factory=_boom)
    assert "# 心理学拆解报告" in out
    assert "记忆功能不可用" in out          # 警告并入返回文本
    assert "已落盘案例" not in out
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/mcp_server/test_tools.py -v`
Expected: 新增 4 个 FAIL — `ImportError: cannot import name 'teardown_tool'`

- [ ] **Step 3: 实现** — 在 `tools.py` 末尾追加:

```python
def teardown_tool(
    description: str,
    *,
    store: Path,
    llm: LLMProvider,
    embed_factory: Callable[[], EmbeddingProvider],
    use_memory: bool = False,
    use_strategies: bool = False,
    self_review: bool = False,
) -> str:
    """MCP teardown:拆解产品描述 → Markdown 报告文本(默认落盘案例)。"""
    text = (description or "").strip()
    if not text:
        return "错误:输入为空。"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    o = analyze_product(llm, text, store=store, now=now,
                        embed_factory=embed_factory, use_memory=use_memory,
                        use_strategies=use_strategies, self_review=self_review)
    parts = [o.rendered]
    if o.case_id:
        parts.append(f"已落盘案例 {o.case_id}")
    parts.extend(o.warnings)
    return "\n\n".join(parts)
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/mcp_server/ -v`
Expected: 全部 passed(8 个)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/mcp_server/tools.py tests/mcp_server/test_tools.py
git commit -m "feat(mcp): teardown_tool — full report text with warnings appended"
```

---

### Task 4: similar / kb_list / kb_show / memory_stats 工具

**Files:**
- Modify: `src/psyteardown/mcp_server/tools.py`(追加)
- Test: `tests/mcp_server/test_tools.py`(追加)

- [ ] **Step 1: 写失败测试** — 追加:

```python
def test_similar_tool_finds_seeded_case(tmp_path):
    from psyteardown.mcp_server.tools import similar_tool, teardown_tool
    store = tmp_path / "cases.db"
    teardown_tool("社交产品:动态推送点赞", store=store,
                  llm=_fake_llm(), embed_factory=_fake_embed_factory)
    out = similar_tool("社交产品:群组动态", store=store,
                       embed_factory=_fake_embed_factory)
    assert "样例产品" in out                  # fake LLM 的产品名


def test_similar_tool_empty_store(tmp_path):
    from psyteardown.mcp_server.tools import similar_tool
    out = similar_tool("任意描述", store=tmp_path / "empty.db",
                       embed_factory=_fake_embed_factory)
    assert "空" in out


def test_similar_tool_empty_description(tmp_path):
    from psyteardown.mcp_server.tools import similar_tool
    out = similar_tool(" ", store=tmp_path / "cases.db",
                       embed_factory=_fake_embed_factory)
    assert out == "错误:输入为空。"


def test_kb_list_tool_contains_seed(tmp_path):
    from psyteardown.mcp_server.tools import kb_list_tool
    out = kb_list_tool(store=tmp_path / "cases.db")
    assert "fogg-behavior-model" in out


def test_kb_show_tool_found_and_missing(tmp_path):
    from psyteardown.mcp_server.tools import kb_show_tool
    store = tmp_path / "cases.db"
    assert "心流" in kb_show_tool("flow", store=store)
    assert "未找到框架:nope" == kb_show_tool("nope", store=store)


def test_memory_stats_tool(tmp_path):
    from psyteardown.mcp_server.tools import memory_stats_tool, teardown_tool
    store = tmp_path / "cases.db"
    assert memory_stats_tool(store=store) == "案例数:0"
    teardown_tool("社交产品:动态推送点赞", store=store,
                  llm=_fake_llm(), embed_factory=_fake_embed_factory)
    assert memory_stats_tool(store=store) == "案例数:1"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/mcp_server/test_tools.py -v`
Expected: 新增 6 个 FAIL — ImportError(similar_tool 等不存在)

- [ ] **Step 3: 实现** — 在 `tools.py` 末尾追加:

```python
def similar_tool(
    description: str,
    top_k: int = 3,
    *,
    store: Path,
    embed_factory: Callable[[], EmbeddingProvider],
) -> str:
    """MCP similar:检索最相似的历史案例,返回文本列表。"""
    text = (description or "").strip()
    if not text:
        return "错误:输入为空。"
    emb = embed_factory()
    hits = search_similar(CaseStore(store), emb, text, top_k=top_k)
    if not hits:
        return "案例库为空或无相似案例。"
    return "\n".join(
        f"{score:.3f}  {case.product_name} — {case.one_liner}"
        f"  ({', '.join(case.frameworks_used) or '—'})"
        for case, score in hits
    )


def kb_list_tool(*, store: Path) -> str:
    """MCP kb_list:列出全部框架(含已批准习得框架)。"""
    return "\n".join(
        f"{fw.id}\t{fw.name}\t({fw.category})"
        for fw in load_frameworks(learned_dir=GrowthStore(store.parent).learned_dir())
    )


def kb_show_tool(framework_id: str, *, store: Path) -> str:
    """MCP kb_show:查看某框架详情;不存在 → 错误文本。"""
    for fw in load_frameworks(learned_dir=GrowthStore(store.parent).learned_dir()):
        if fw.id == framework_id:
            lines = [f"# {fw.name} ({fw.id})", fw.summary, ""]
            lines += [
                f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})"
                for p in fw.principles
            ]
            return "\n".join(lines)
    return f"未找到框架:{framework_id}"


def memory_stats_tool(*, store: Path) -> str:
    """MCP memory_stats:案例库统计。"""
    return f"案例数:{CaseStore(store).count()}"
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/mcp_server/ -v`
Expected: 全部 passed(14 个)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/mcp_server/tools.py tests/mcp_server/test_tools.py
git commit -m "feat(mcp): similar/kb_list/kb_show/memory_stats tools"
```

---

### Task 5: review_case_tool

**Files:**
- Modify: `src/psyteardown/mcp_server/tools.py`(追加)
- Test: `tests/mcp_server/test_tools.py`(追加)

- [ ] **Step 1: 写失败测试** — 追加:

```python
def test_review_case_tool_backfills(tmp_path):
    from psyteardown.llm.base import FakeProvider
    from psyteardown.memory.store import CaseStore
    from psyteardown.mcp_server.tools import review_case_tool, teardown_tool

    store = tmp_path / "cases.db"
    teardown_tool("社交产品:动态推送点赞", store=store,
                  llm=_fake_llm(), embed_factory=_fake_embed_factory)
    cid = [c for c, _ in CaseStore(store).all()][0].case_id

    review_llm = FakeProvider(structured_responses=[
        CaseReview(score=0.4, weaknesses=["置信虚高"], suggestions=["核对数据"]),
    ])
    out = review_case_tool(cid, store=store, llm=review_llm)
    assert "总体评分 0.40" in out
    assert "置信虚高" in out
    assert CaseStore(store).get(cid).review.score == 0.4


def test_review_case_tool_missing(tmp_path):
    from psyteardown.mcp_server.tools import review_case_tool
    out = review_case_tool("nope", store=tmp_path / "cases.db", llm=_fake_llm())
    assert out == "案例不存在:nope"
```

同时在文件顶部 import 区补:`from psyteardown.review.models import CaseReview`。

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/mcp_server/test_tools.py -v`
Expected: 新增 2 个 FAIL — ImportError(review_case_tool 不存在)

- [ ] **Step 3: 实现** — 在 `tools.py` 末尾追加:

```python
def review_case_tool(case_id: str, *, store: Path, llm: LLMProvider) -> str:
    """MCP review_case:对历史案例补做批判自评(覆盖旧自评,保留向量)。

    用户显式要求自评:LLM 失败让异常向上抛(server 层转错误文本),不静默。
    不含 --to-reflect(策略蒸馏属管理操作,留 CLI)。
    """
    case_store = CaseStore(store)
    hit = case_store.get_with_embedding(case_id)
    if hit is None:
        return f"案例不存在:{case_id}"
    case, emb = hit
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rev = review_case(llm, case.result, reviewed_at=now,
                      model_label=case.result.meta.model)
    case.review = rev
    case_store.save(case, emb)
    lines = [f"自评完成:{case_id} 总体评分 {rev.score:.2f}"]
    lines += [f"- 缺陷:{w}" for w in rev.weaknesses]
    lines += [f"- 建议:{s}" for s in rev.suggestions]
    return "\n".join(lines)
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/mcp_server/ -v`
Expected: 全部 passed(16 个)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/mcp_server/tools.py tests/mcp_server/test_tools.py
git commit -m "feat(mcp): review_case_tool — backfill self-critique via MCP"
```

---

### Task 6: server.py(FastMCP 装配 + main 入口)

**Files:**
- Create: `src/psyteardown/mcp_server/server.py`
- Test: `tests/mcp_server/test_server.py`(新建)

- [ ] **Step 1: 写失败测试**

创建 `tests/mcp_server/test_server.py`:

```python
"""server 装配测试:需要 mcp 包(未装则整文件跳过)。"""

import asyncio

import pytest

pytest.importorskip("mcp")


def test_build_server_registers_six_tools():
    from psyteardown.mcp_server.server import build_server

    srv = build_server()
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert names == {"teardown", "similar", "review_case",
                     "kb_list", "kb_show", "memory_stats"}


def test_main_without_mcp_gives_install_hint(monkeypatch, capsys):
    import builtins

    from psyteardown.mcp_server import server

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError("No module named 'mcp'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code == 1
    assert "pip install" in capsys.readouterr().err
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/mcp_server/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.mcp_server.server'`

- [ ] **Step 3: 实现**

创建 `src/psyteardown/mcp_server/server.py`:

```python
"""MCP server 装配:环境变量 → 依赖,FastMCP 注册 6 工具,stdio 传输。零业务逻辑。

mcp 包只在本模块内 import(可选依赖);tools.py 保持零 mcp 依赖。
"""

import os
import sys
from pathlib import Path

from psyteardown.mcp_server import tools


def _store() -> Path:
    return Path(os.environ.get("PSYTEARDOWN_STORE", str(tools.DEFAULT_STORE)))


def _llm():
    return tools.build_llm_provider(os.environ.get("PSYTEARDOWN_LLM", "claude"))


def _embed():
    return tools.build_embed_provider(os.environ.get("PSYTEARDOWN_EMBED", "local"))


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("psyteardown")

    def _guard(fn, *args, **kwargs) -> str:
        """统一错误壳:领域异常转清晰文本,不裸抛堆栈进对话。"""
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            return f"错误:{type(e).__name__}: {e}"

    @mcp.tool()
    def teardown(description: str, use_memory: bool = False,
                 use_strategies: bool = False, self_review: bool = False) -> str:
        """基于心理学框架拆解一个产品的文字描述,返回完整 Markdown 报告并落盘案例。
        当用户想分析/拆解某个产品的心理机制、成瘾设计、用户体验时使用。
        use_memory=检索相似历史案例注入;use_strategies=注入已批准策略卡;
        self_review=拆解后追加批判性自评。耗时可达数分钟,请耐心等待。"""
        return _guard(tools.teardown_tool, description, store=_store(),
                      llm=_llm(), embed_factory=_embed,
                      use_memory=use_memory, use_strategies=use_strategies,
                      self_review=self_review)

    @mcp.tool()
    def similar(description: str, top_k: int = 3) -> str:
        """按产品描述检索最相似的历史拆解案例(向量余弦)。"""
        return _guard(tools.similar_tool, description, top_k,
                      store=_store(), embed_factory=_embed)

    @mcp.tool()
    def review_case(case_id: str) -> str:
        """对指定 case_id 的历史案例补做批判性自评(覆盖旧自评)。"""
        return _guard(tools.review_case_tool, case_id,
                      store=_store(), llm=_llm())

    @mcp.tool()
    def kb_list() -> str:
        """列出心理学框架知识库(含已批准的习得框架)。"""
        return _guard(tools.kb_list_tool, store=_store())

    @mcp.tool()
    def kb_show(framework_id: str) -> str:
        """查看某个心理学框架的详情(原则 + 识别线索)。"""
        return _guard(tools.kb_show_tool, framework_id, store=_store())

    @mcp.tool()
    def memory_stats() -> str:
        """案例库统计(案例数)。"""
        return _guard(tools.memory_stats_tool, store=_store())

    return mcp


def main() -> None:
    try:
        import mcp  # noqa: F401
    except ImportError:
        print('未安装 mcp 包。请先安装:pip install -e ".[mcp]"', file=sys.stderr)
        raise SystemExit(1)
    build_server().run()          # stdio 传输(FastMCP 默认)
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest tests/mcp_server/ -v`
Expected: 全部 passed(18 个)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/mcp_server/server.py tests/mcp_server/test_server.py
git commit -m "feat(mcp): FastMCP server — 6 tools over stdio, env-driven deps"
```

---

### Task 7: README、版本文案、全量回归、冒烟

**Files:**
- Modify: `README.md`
- Modify: `src/psyteardown/cli.py:28`(Typer help 版本号)

- [ ] **Step 1: 更新 README**

1. 标题 `(v5)` → `(v6)`;首段末尾补:`v6 交付层(MCP server,Claude 对话中直接调用)。`
2. 「安装」节后新增一节:

```markdown
## MCP 接入(Claude Code / Claude Desktop)

    pip install -e ".[mcp]"

Claude Code 一条命令接入(环境变量按需增减;store 建议绝对路径):

    claude mcp add psyteardown \
      -e PSYTEARDOWN_LLM=deepseek -e DEEPSEEK_API_KEY=sk-... \
      -e PSYTEARDOWN_EMBED=ollama \
      -e PSYTEARDOWN_STORE=D:/app/app-mental/.psyteardown/cases.db \
      -- psyteardown-mcp

Claude Desktop 在 `claude_desktop_config.json` 的 `mcpServers` 里加:

    "psyteardown": {
      "command": "psyteardown-mcp",
      "env": { "PSYTEARDOWN_LLM": "deepseek", "DEEPSEEK_API_KEY": "sk-...",
               "PSYTEARDOWN_EMBED": "ollama",
               "PSYTEARDOWN_STORE": "D:/app/app-mental/.psyteardown/cases.db" }
    }

对话中即可说「帮我拆解这个产品:……」触发 teardown 工具。
暴露工具:teardown / similar / review_case / kb_list / kb_show / memory_stats。
管理操作(learn / strategize / candidates / strategies 审批)仍走 CLI。
```

3. 架构列表加一行(`review` 行之后):

```
- `mcp_server` — 交付层:MCP server(FastMCP/stdio),6 工具;与 CLI 共享编排
```

- [ ] **Step 2: CLI help 版本号**

`src/psyteardown/cli.py` 第 28 行:`Agent(v5)` → `Agent(v6)`。

- [ ] **Step 3: 全量回归 + 冒烟**

Run: `python -m pytest 2>&1 | tail -1`
Expected: **191 passed, 2 skipped**(175 基线 + 16 新增),0 failed

Run: `python -c "import asyncio; from psyteardown.mcp_server.server import build_server; print(len(asyncio.run(build_server().list_tools())))"`
Expected: `6`

- [ ] **Step 4: 提交**

```bash
git add README.md src/psyteardown/cli.py
git commit -m "docs: MCP integration guide; bump to v6"
```

---

## 计划自审(已执行)

- **Spec 覆盖**:成功标准 1(T3–T6:6 工具 + entry point T1)、2(T7 README `claude mcp add`)、3(T6 环境变量装配,`PSYTEARDOWN_STORE` 新增)、4(tools.py 零 mcp 依赖 T2–T5,全 Fake 测试)、5(T6 `_guard` 错误壳)、6(T2 提取共享编排 + 回归锁 Step 6)。YAGNI 清单均未实现 ✓。
- **占位符扫描**:无 TBD/TODO;所有代码步骤含完整代码。
- **类型一致性**:`analyze_product(llm, description, *, store, now, embed_factory, use_memory, no_save, use_strategies, self_review, fmt)` 在 T2 定义、T2 CLI 调用、T3 teardown_tool 调用一致;`AnalyzeOutcome(rendered, case_id, warnings)` 各处一致;`build_llm_provider`/`build_embed_provider` 在 T2 定义、CLI 别名、T6 server 使用一致;6 个工具函数签名 T3–T5 定义与 T6 注册调用一致。
- **顺序依赖**:T2 依赖 T1(包存在);T3–T5 依赖 T2;T6 依赖 T3–T5;T7 最后。按序执行。
- **风险注记**:T6 的 `srv.list_tools()`(async)是 mcp 1.x FastMCP 公开方法;若安装版本 API 不同,实现者应查 `mcp.server.fastmcp.FastMCP` 实际接口并等价替换断言取数方式(工具名集合不变),不得跳过测试。
