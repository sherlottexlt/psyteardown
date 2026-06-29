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
