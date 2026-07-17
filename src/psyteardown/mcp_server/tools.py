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
    review_fn: Callable = review_case,
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
            review_obj = review_fn(llm, result, reviewed_at=now,
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
