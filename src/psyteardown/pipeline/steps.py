"""拆解流水线 5 步。每步:输入 → 输出;LLM 调用经注入的 provider。"""

from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMError, LLMProvider
from psyteardown.pipeline.schemas import (
    ExperienceAssessment,
    GroundingStats,
    Mapping,
    MappingList,
    ProductProfile,
    Synthesis,
)
from psyteardown.kb.retriever import retrieve_frameworks
from psyteardown.pipeline.grounding import is_grounded

_SYSTEM = "你是资深产品体验与行为心理学分析师。只依据给定框架做拆解,不要编造心理学理论。"


def parse_product(provider: LLMProvider, description: str) -> ProductProfile:
    """Step 1:把自由文本归一成结构化产品画像(不涉及心理学)。"""
    prompt = (
        "请把下面的产品描述解析成结构化画像:产品名、类型、一句话定位、"
        "核心功能列表(每个含名称/描述/用户目标)、关键体验触点。\n\n"
        f"产品描述:\n{description}"
    )
    return provider.structured_complete(prompt, ProductProfile, system=_SYSTEM)


def retrieve(
    profile: ProductProfile,
    library: list[Framework],
    max_n: int = 8,
    min_n: int = 5,
) -> list[Framework]:
    """Step 2:纯代码,按产品类型/功能/触点关键词检索相关框架。"""
    keywords = [profile.product_type, *profile.touchpoints]
    keywords += [f.name for f in profile.features]
    return retrieve_frameworks(library, keywords=keywords, max_n=max_n, min_n=min_n)


def _frameworks_brief(frameworks: list[Framework]) -> str:
    lines = []
    for fw in frameworks:
        ps = "; ".join(
            f"{p.id}:{p.name}(线索:{'/'.join(p.look_for)})" for p in fw.principles
        )
        lines.append(f"- [{fw.id}] {fw.name} — {fw.summary} 原则: {ps}")
    return "\n".join(lines)


def map_features(
    provider: LLMProvider,
    profile: ProductProfile,
    frameworks: list[Framework],
    description: str,
    prior_summary: str | None = None,
    strategy_guidance: str | None = None,
) -> tuple[list[Mapping], GroundingStats]:
    """Step 3:逐功能/触点映射到框架原则。单项失败标 error 并继续。

    description=产品原文,evidence 的唯一合法来源:prompt 要求逐字引用,
    is_grounded 校验,未通过的映射丢弃并记入 GroundingStats(spec 2026-09-02)。
    prior_summary=历史相似案例;strategy_guidance=历史归纳的拆解策略(均仅供参考)。"""
    brief = _frameworks_brief(frameworks)
    valid_ids = ", ".join(fw.id for fw in frameworks)
    ref_block = ""
    if prior_summary:
        ref_block = (
            "\n以下是仅供参考的历史相似案例,请独立判断当前产品,不要照搬:\n"
            f"{prior_summary}\n"
        )
    if strategy_guidance:
        ref_block += (
            "\n以下是历史归纳的拆解策略,供参考,请结合当前产品独立判断:\n"
            f"{strategy_guidance}\n"
        )
    targets = [f.name for f in profile.features] + profile.touchpoints
    mappings: list[Mapping] = []
    stats = GroundingStats()
    for target in targets:
        prompt = (
            f"产品原文(evidence 的唯一合法来源):\n{description}\n\n"
            f"可用心理学框架:\n{brief}\n"
            f"{ref_block}\n"
            f"产品「{profile.name}」的功能/触点:「{target}」。\n"
            "请判断它用到了哪个框架的哪条原则、为何有效,并给出 0-1 的置信度。"
            f"framework_id 必须来自这些 id: {valid_ids}。"
            "若适用多条,返回最贴切的若干条 mapping。\n"
            "字段硬性要求:\n"
            "- evidence 必须是上方产品原文中的一段连续原文,逐字复制,不得改写、拼接、增删;\n"
            "- 原文中找不到支持该判断的文字,就不要产出这条 mapping;宁可少给,不可编造;\n"
            "- 一切解读、推理、心理学解释写进 rationale,不得写进 evidence。"
        )
        try:
            result = provider.structured_complete(prompt, MappingList, system=_SYSTEM)
        except LLMError as e:
            mappings.append(
                Mapping(
                    feature=target, framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error=str(e),
                )
            )
            continue
        for m in result.mappings:
            m.feature = target  # 幽灵功能名以调用目标为准;细分意图在 rationale
            if is_grounded(m.evidence, description):
                mappings.append(m)
                stats.kept += 1
            else:
                stats.dropped += 1
                stats.dropped_mappings.append(m)
    return mappings, stats


def assess_experience(
    provider: LLMProvider,
    profile: ProductProfile,
    mappings: list[Mapping],
    strategy_guidance: str | None = None,
) -> ExperienceAssessment:
    """Step 4:整体体验评估 + 暗黑模式/伦理标注。
    strategy_guidance=历史归纳的评估策略(仅供参考)。"""
    mapping_lines = "\n".join(
        f"- {m.feature}: {m.framework_id}.{m.principle_id} — {m.evidence}"
        for m in mappings
        if not m.error
    )
    guide = ""
    if strategy_guidance:
        guide = ("\n以下是历史归纳的拆解策略,供参考,请结合当前产品独立判断:\n"
                 f"{strategy_guidance}\n")
    prompt = (
        f"产品:{profile.name}({profile.one_liner})。\n"
        f"已识别的心理学机制:\n{mapping_lines}\n"
        f"{guide}\n"
        "请给出整体体验评估:优势、摩擦点、伦理/暗黑模式警示、机会点。"
    )
    return provider.structured_complete(prompt, ExperienceAssessment, system=_SYSTEM)


def synthesize(
    provider: LLMProvider,
    profile: ProductProfile,
    mappings: list[Mapping],
    assessment: ExperienceAssessment,
) -> str:
    """Step 5:综合成 executive summary。"""
    prompt = (
        f"产品:{profile.name}。优势:{assessment.strengths};"
        f"摩擦:{assessment.friction_points};伦理警示:{assessment.ethics_warnings}。\n"
        "请写一段简洁的高管摘要(executive summary),概述该产品的心理学拆解结论。"
    )
    return provider.structured_complete(prompt, Synthesis, system=_SYSTEM).executive_summary
