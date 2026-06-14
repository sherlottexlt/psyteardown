"""拆解流水线 5 步。每步:输入 → 输出;LLM 调用经注入的 provider。"""

from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMError, LLMProvider
from psyteardown.pipeline.schemas import (
    ExperienceAssessment,
    Mapping,
    MappingList,
    ProductProfile,
    Synthesis,
)
from psyteardown.kb.retriever import retrieve_frameworks

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
    profile: ProductProfile, library: list[Framework], top_n: int = 5
) -> list[Framework]:
    """Step 2:纯代码,按产品类型/功能/触点关键词检索相关框架。"""
    keywords = [profile.product_type, *profile.touchpoints]
    keywords += [f.name for f in profile.features]
    return retrieve_frameworks(library, keywords=keywords, top_n=top_n)


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
) -> list[Mapping]:
    """Step 3:逐功能/触点映射到框架原则。单项失败标 error 并继续。"""
    brief = _frameworks_brief(frameworks)
    valid_ids = ", ".join(fw.id for fw in frameworks)
    targets = [f.name for f in profile.features]
    mappings: list[Mapping] = []
    for target in targets:
        prompt = (
            f"可用心理学框架:\n{brief}\n\n"
            f"产品「{profile.name}」的功能/触点:「{target}」。\n"
            "请判断它用到了哪个框架的哪条原则、在产品中的具体体现、为何有效,"
            "并给出 0-1 的置信度。framework_id 必须来自这些 id: "
            f"{valid_ids}。若适用多条,返回最贴切的若干条 mapping。"
        )
        try:
            result = provider.structured_complete(prompt, MappingList, system=_SYSTEM)
            mappings.extend(result.mappings)
        except LLMError as e:
            mappings.append(
                Mapping(
                    feature=target, framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error=str(e),
                )
            )
    return mappings


def assess_experience(
    provider: LLMProvider,
    profile: ProductProfile,
    mappings: list[Mapping],
) -> ExperienceAssessment:
    """Step 4:整体体验评估 + 暗黑模式/伦理标注。"""
    mapping_lines = "\n".join(
        f"- {m.feature}: {m.framework_id}.{m.principle_id} — {m.evidence}"
        for m in mappings
        if not m.error
    )
    prompt = (
        f"产品:{profile.name}({profile.one_liner})。\n"
        f"已识别的心理学机制:\n{mapping_lines}\n\n"
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
