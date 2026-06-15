"""编排 5 步流水线,产出 TeardownResult。"""

from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMProvider
from psyteardown.llm.claude import DEFAULT_MODEL
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import (
    FrameworkCitation,
    TeardownMeta,
    TeardownResult,
)


def run_teardown(
    provider: LLMProvider,
    description: str,
    library: list[Framework],
    *,
    generated_at: str,
    model_label: str | None = None,
    top_n: int = 5,
) -> TeardownResult:
    """跑完整流水线。generated_at 由调用方传入(脚本环境禁用 datetime.now)。"""
    profile = steps.parse_product(provider, description)
    frameworks = steps.retrieve(profile, library, top_n=top_n)
    mappings = steps.map_features(provider, profile, frameworks)
    assessment = steps.assess_experience(provider, profile, mappings)
    summary = steps.synthesize(provider, profile, mappings, assessment)

    return TeardownResult(
        product=profile,
        frameworks_used=[fw.id for fw in frameworks],
        citations=[
            FrameworkCitation(id=fw.id, name=fw.name, references=fw.references)
            for fw in frameworks
        ],
        mappings=mappings,
        assessment=assessment,
        executive_summary=summary,
        meta=TeardownMeta(
            model=model_label or _provider_label(provider),
            generated_at=generated_at,
        ),
    )


def _provider_label(provider: LLMProvider) -> str:
    """从 provider 取一个可读模型标签;FakeProvider → 'fake'。"""
    cls = type(provider).__name__
    if cls == "ClaudeProvider":
        return getattr(provider, "_model", DEFAULT_MODEL)
    return "fake"
