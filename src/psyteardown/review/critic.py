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
