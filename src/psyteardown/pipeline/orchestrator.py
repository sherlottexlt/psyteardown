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
from psyteardown.strategy.models import StrategyCard
from psyteardown.strategy.select import select_for


def run_teardown(
    provider: LLMProvider,
    description: str,
    library: list[Framework],
    *,
    generated_at: str,
    model_label: str | None = None,
    max_n: int = 8,
    min_n: int = 5,
    prior_summary: str | None = None,
    strategy_cards: list[StrategyCard] | None = None,
) -> TeardownResult:
    """跑完整流水线。generated_at 由调用方传入(脚本环境禁用 datetime.now)。
    prior_summary 注入 step3;strategy_cards 按 target_step 分发注入 step3/step4。"""
    profile = steps.parse_product(provider, description)
    frameworks = steps.retrieve(profile, library, max_n=max_n, min_n=min_n)
    map_guide = select_for(strategy_cards, profile, "mapping") if strategy_cards else None
    assess_guide = select_for(strategy_cards, profile, "assessment") if strategy_cards else None
    mappings = steps.map_features(provider, profile, frameworks,
                                  prior_summary=prior_summary,
                                  strategy_guidance=map_guide or None)
    assessment = steps.assess_experience(provider, profile, mappings,
                                         strategy_guidance=assess_guide or None)
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
    if cls == "FakeProvider":
        return "fake"
    if cls == "ClaudeProvider":
        return getattr(provider, "_model", DEFAULT_MODEL)
    # 其他 provider(如 DeepSeekProvider)约定公开 model 属性;都没有则回退类名
    return getattr(provider, "model", cls)
