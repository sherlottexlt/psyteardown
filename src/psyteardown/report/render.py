"""把 TeardownResult 渲染成 Markdown 或 JSON。"""

from psyteardown.pipeline.schemas import TeardownResult

LOW_CONFIDENCE = 0.5


def render_json(result: TeardownResult) -> str:
    return result.model_dump_json(indent=2)


def render_markdown(result: TeardownResult) -> str:
    p = result.product
    out: list[str] = []

    # 1. 概述
    out.append(f"# 心理学拆解报告:{p.name}\n")
    out.append("## 概述\n")
    out.append(f"**{p.one_liner}**\n")
    out.append(f"{result.executive_summary}\n")

    # 2. 产品画像
    out.append("## 产品画像\n")
    out.append(f"- 类型:{p.product_type}")
    out.append(f"- 关键触点:{', '.join(p.touchpoints) or '—'}")
    out.append("- 核心功能:")
    for f in p.features:
        out.append(f"  - **{f.name}** — {f.description}(用户目标:{f.user_goal})")
    out.append("")

    # 3. 逐功能心理学拆解
    out.append("## 逐功能心理学拆解\n")
    for m in result.mappings:
        if m.error:
            out.append(f"- ⚠️ **{m.feature}**:映射失败({m.error})")
            continue
        flag = " ⚠️低置信" if m.confidence < LOW_CONFIDENCE else ""
        out.append(
            f"- **{m.feature}** → `{m.framework_id}·{m.principle_id}`"
            f"(置信 {m.confidence:.2f}{flag})\n"
            f"  - 体现:{m.evidence}\n"
            f"  - 为何有效:{m.rationale}"
        )
    out.append("")

    # 4. 整体体验评估
    a = result.assessment
    out.append("## 整体体验评估\n")
    out.append(f"- 优势:{_join(a.strengths)}")
    out.append(f"- 摩擦点:{_join(a.friction_points)}")
    out.append("")

    # 5. 伦理 / 暗黑模式提示
    out.append("## ⚠️ 伦理 / 暗黑模式提示\n")
    if a.ethics_warnings:
        for w in a.ethics_warnings:
            out.append(f"- {w}")
    else:
        out.append("- 未发现明显风险")
    out.append("")

    # 6. 机会点
    out.append("## 机会点\n")
    for o in a.opportunities or ["—"]:
        out.append(f"- {o}")
    out.append("")

    # 7. 附录
    out.append("## 附录:引用框架\n")
    for fid in result.frameworks_used:
        out.append(f"- {fid}")
    out.append(f"\n_模型:{result.meta.model} · 生成时间:{result.meta.generated_at}_")

    return "\n".join(out)


def _join(items: list[str]) -> str:
    return "；".join(items) if items else "—"
