"""按 target_step + applies_to 选出适用策略卡,拼成注入指引文本。纯代码。"""

from psyteardown.strategy.models import StrategyCard
from psyteardown.pipeline.schemas import ProductProfile

_VALID_STEPS = ("retrieval", "mapping", "assessment")


def _applies(card: StrategyCard, profile: ProductProfile) -> bool:
    if not card.applies_to:
        return True                      # 空 = 通配
    haystacks = [profile.product_type] + [f.name for f in profile.features]
    for term in card.applies_to:
        if not term:                     # 跳过空串,避免误通配
            continue
        for h in haystacks:
            if term in h or h in term:   # 子串双向匹配(同 v1 检索器风格)
                return True
    return False


def select_for(cards: list[StrategyCard], profile: ProductProfile, step: str) -> str:
    """step=="mapping" 时并入 retrieval 类(标注「检索层建议」);
    step=="assessment" 只取 assessment 类。applies_to 命中当前产品才入选。无命中→''。"""
    wanted = {step}
    if step == "mapping":
        wanted.add("retrieval")
    lines: list[str] = []
    for c in cards:
        if c.target_step not in wanted or not _applies(c, profile):
            continue
        tag = "(检索层建议)" if c.target_step == "retrieval" else ""
        lines.append(f"- {c.rule}{tag}")
    return "\n".join(lines)
