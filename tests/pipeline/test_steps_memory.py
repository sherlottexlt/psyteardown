from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList,
)


def _fw():
    return Framework(
        id="habit", name="上瘾模型", category="habit", summary="s", tags=["签到"],
        principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
        references=["r"],
    )


def _profile():
    return ProductProfile(
        name="Demo", product_type="App", one_liner="x",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=[],
    )


def _mapping():
    return Mapping(feature="签到", framework_id="habit", principle_id="trigger",
                   rationale="r", evidence="e", confidence=0.9)


def test_prior_summary_injected_into_step3_prompt():
    provider = FakeProvider(structured_responses=[MappingList(mappings=[_mapping()])])
    steps.map_features(provider, _profile(), [_fw()], "每日签到App描述",
                       prior_summary="- 旧产品X(一句话):用过框架 hook-model")
    prompt = provider.calls[0]["prompt"]
    assert "旧产品X" in prompt
    assert "仅供参考" in prompt  # 防照搬提示


def test_no_prior_summary_means_no_reference_block():
    provider = FakeProvider(structured_responses=[MappingList(mappings=[_mapping()])])
    steps.map_features(provider, _profile(), [_fw()], "每日签到App描述")  # 默认 None
    assert "仅供参考" not in provider.calls[0]["prompt"]
