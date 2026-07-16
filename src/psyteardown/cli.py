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
from psyteardown.review.critic import review_case
from psyteardown.review.models import CaseReview
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, Synthesis,
)
from psyteardown.growth.store import GrowthStore
from psyteardown.growth.proposer import propose_frameworks
from psyteardown.growth.dedup import filter_duplicates
from psyteardown.strategy.store import StrategyStore
from psyteardown.strategy.proposer import propose_strategies
from psyteardown.strategy.distill import distill_from_note

app = typer.Typer(help="心理驱动型产品拆解 Agent(v4)")
kb_app = typer.Typer(help="知识库操作")
memory_app = typer.Typer(help="案例库操作")
candidates_app = typer.Typer(help="习得框架候选:审阅/批准/驳回")
strategies_app = typer.Typer(help="拆解策略卡:审阅/批准/驳回")
app.add_typer(kb_app, name="kb")
app.add_typer(memory_app, name="memory")
app.add_typer(candidates_app, name="candidates")
app.add_typer(strategies_app, name="strategies")

DEFAULT_STORE = Path(".psyteardown/cases.db")


def _growth_store(store: Path) -> GrowthStore:
    return GrowthStore(store.parent)


def _strategy_store(store: Path) -> StrategyStore:
    return StrategyStore(store.parent)


def _build_provider(name: str) -> LLMProvider:
    if name == "fake":
        return FakeProvider(structured_responses=[
            ProductProfile(name="样例产品", product_type="App",
                           one_liner="自动生成的占位画像", features=[], touchpoints=[]),
            ExperienceAssessment(),
            Synthesis(executive_summary="(fake provider 占位摘要)"),
            CaseReview(score=0.5, suggestions=["(fake) 占位改进建议"]),
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
    use_strategies: bool = typer.Option(False, "--use-strategies", help="注入已批准的拆解策略卡"),
    self_review: bool = typer.Option(False, "--self-review",
                                     help="拆解后追加一次 LLM 自评(默认关)"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True),
):
    """拆解一个产品描述,输出结构化报告;默认落盘为案例。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)

    library = load_frameworks(learned_dir=_growth_store(store).learned_dir())
    llm = _build_provider(provider)

    # 记忆是增强,不应让其失败(如离线无嵌入模型)拖垮核心拆解。
    emb: EmbeddingProvider | None = None
    case_store: CaseStore | None = None
    if use_memory or not no_save:
        try:
            emb = _build_embed_provider(embed_provider)
            case_store = CaseStore(store)
        except Exception as e:  # noqa: BLE001 — 记忆不可用时降级,不中断拆解
            typer.echo(f"提示:记忆功能不可用({e}),本次跳过案例库。", err=True)
            emb = case_store = None

    prior_summary: str | None = None
    if use_memory and case_store is not None and emb is not None:
        try:
            hits = search_similar(case_store, emb, text, top_k=3)
            prior_summary = summarize_cases([c for c, _ in hits]) or None
        except Exception as e:  # noqa: BLE001
            typer.echo(f"提示:相似案例检索失败({e}),本次不注入历史参考。", err=True)

    strategy_cards = None
    if use_strategies:
        strategy_cards = _strategy_store(store).list_approved()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    result = run_teardown(llm, text, library=library, generated_at=now,
                          prior_summary=prior_summary, strategy_cards=strategy_cards)

    # 自评是增强:失败降级,不拖垮报告(与记忆功能同风格)。
    review_obj: CaseReview | None = None
    if self_review:
        try:
            review_obj = review_case(llm, result, reviewed_at=now,
                                     model_label=result.meta.model)
        except Exception as e:  # noqa: BLE001
            typer.echo(f"提示:自评失败({e}),报告不含自评节。", err=True)

    rendered = (render_json(result, review=review_obj) if fmt == "json"
                else render_markdown(result, review=review_obj))
    if out:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)

    if not no_save and case_store is not None and emb is not None:
        try:
            case = Case.from_result(result, description=text, created_at=now)
            case.review = review_obj
            case_store.save(case, emb.embed([text])[0])
            typer.echo(f"已落盘案例 {case.case_id}")
        except Exception as e:  # noqa: BLE001
            typer.echo(f"提示:案例落盘失败({e}),报告已照常产出。", err=True)


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
def kb_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径(用于合并习得框架)"),
):
    """列出已加载的框架(含已批准的习得框架)。"""
    for fw in load_frameworks(learned_dir=_growth_store(store).learned_dir()):
        typer.echo(f"{fw.id}\t{fw.name}\t({fw.category})")


@kb_app.command("show")
def kb_show(
    framework_id: str = typer.Argument(..., help="框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径(用于合并习得框架)"),
):
    """查看某框架详情(含已批准的习得框架)。"""
    for fw in load_frameworks(learned_dir=_growth_store(store).learned_dir()):
        if fw.id == framework_id:
            typer.echo(f"# {fw.name} ({fw.id})\n{fw.summary}\n")
            for p in fw.principles:
                typer.echo(f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})")
            return
    typer.echo(f"未找到框架:{framework_id}", err=True)
    raise typer.Exit(code=1)


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
    from psyteardown.growth.store import GrowthError

    try:
        c = _growth_store(store).get_candidate(framework_id)
    except GrowthError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
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
    from psyteardown.strategy.store import StrategyError

    try:
        c = _strategy_store(store).get_candidate(strategy_id)
    except StrategyError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
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
