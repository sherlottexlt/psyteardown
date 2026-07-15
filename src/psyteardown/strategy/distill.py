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
