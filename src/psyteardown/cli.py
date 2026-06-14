"""薄 CLI:读输入 → 调内核 → 写输出。零业务逻辑。"""

from datetime import datetime
from pathlib import Path

import typer

from psyteardown.kb.loader import load_frameworks
from psyteardown.llm.base import FakeProvider, LLMProvider
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.report.render import render_json, render_markdown
from psyteardown.pipeline.schemas import (
    ProductProfile, MappingList, ExperienceAssessment, Synthesis,
)

app = typer.Typer(help="心理驱动型产品拆解 Agent(v1)")
kb_app = typer.Typer(help="知识库操作")
app.add_typer(kb_app, name="kb")


def _build_provider(name: str) -> LLMProvider:
    if name == "fake":
        # 仅用于测试:返回可跑通流水线的固定结构(无需真实 API)
        return FakeProvider(structured_responses=[
            ProductProfile(name="样例产品", product_type="App",
                           one_liner="自动生成的占位画像", features=[], touchpoints=[]),
            ExperienceAssessment(),  # 无功能/触点 → 无 step3 调用,直接 step4
            Synthesis(executive_summary="(fake provider 占位摘要)"),
        ])
    from psyteardown.llm.claude import ClaudeProvider

    return ClaudeProvider()


@app.command()
def analyze(
    input: Path = typer.Option(..., "--input", "-i", help="产品描述文本文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出文件;省略则打印到终端"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
):
    """拆解一个产品描述,输出结构化报告。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)

    library = load_frameworks()
    llm = _build_provider(provider)
    result = run_teardown(
        llm, text, library=library,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    rendered = render_json(result) if fmt == "json" else render_markdown(result)
    if out:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


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
