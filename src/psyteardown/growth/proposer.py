"""从案例提炼现有框架盖不住的全新框架(结构化输出)。"""

from psyteardown.growth.models import CandidateList, FrameworkCandidate
from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMProvider
from psyteardown.memory.models import Case

_SYSTEM = (
    "你是心理学研究者,擅长从产品行为模式中归纳新的心理学框架。"
    "只在现有框架确实盖不住时才提出新框架,不要复述现有框架。"
)


def _existing_brief(existing: list[Framework]) -> str:
    return "\n".join(f"- {f.id}({f.name}):{f.summary}" for f in existing)


def _case_brief(cases: list[Case]) -> str:
    lines = []
    for c in cases:
        mech = "; ".join(
            f"{m.evidence}(置信{m.confidence:.1f})"
            for m in c.result.mappings
            if not m.error and m.evidence
        )
        lines.append(f"- [{c.case_id}] {c.one_liner}:{mech}")
    return "\n".join(lines)


def propose_frameworks(
    provider: LLMProvider,
    cases: list[Case],
    existing: list[Framework],
    *,
    created_at: str,
    min_support: int = 3,
    max_candidates: int = 5,
) -> list[FrameworkCandidate]:
    """空案例库 → []。要求候选引用 ≥min_support 个真实案例 id,否则丢弃。"""
    if not cases:
        return []
    prompt = (
        f"现有心理学框架(不要重复这些):\n{_existing_brief(existing)}\n\n"
        f"以下是若干产品的心理机制(每行含案例 id):\n{_case_brief(cases)}\n\n"
        "找出反复出现、且上述现有框架都无法很好解释的心理学模式,"
        f"提出至多 {max_candidates} 个全新框架。每个框架给出 id(kebab-case)、name、"
        "category、summary、tags、principles(每条含 id/name/description/look_for)、"
        "其中 tags 与 look_for 必须使用中文(id 保持 kebab-case 英文),"
        "因为检索按中文产品描述与它们做匹配;"
        "references、ethics_notes;在 rationale 说明为何现有框架盖不住,"
        f"在 source_case_ids 列出支撑它的案例 id(至少 {min_support} 个)。"
    )
    out = provider.structured_complete(prompt, CandidateList, system=_SYSTEM)
    valid = {c.case_id for c in cases}
    kept: list[FrameworkCandidate] = []
    for cand in out.candidates:
        support = [cid for cid in cand.source_case_ids if cid in valid]
        if len(support) < min_support:
            continue
        cand.source_case_ids = support
        cand.created_at = created_at
        kept.append(cand)
    return kept[:max_candidates]
