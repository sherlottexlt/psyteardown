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
