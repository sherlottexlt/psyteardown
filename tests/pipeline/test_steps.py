from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider, LLMError
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
    GroundingStats,
)


def _fw(id_, tags):
    return Framework(
        id=id_, name=id_, category="motivation", summary="s", tags=tags,
        principles=[Principle(id="p", name="p", description="d", look_for=["x"])],
        references=["r"],
    )


def _profile():
    return ProductProfile(
        name="Demo", product_type="App", one_liner="x",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=["推送"],
    )


_DESC = "Demo App:每日签到拿奖励,完成后收到推送提醒。"


def test_step1_parse_product():
    provider = FakeProvider(structured_responses=[_profile()])
    profile = steps.parse_product(provider, "一些产品描述文本")
    assert profile.name == "Demo"
    assert "一些产品描述文本" in provider.calls[0]["prompt"]


def test_step2_retrieve_is_pure_no_llm():
    provider = FakeProvider()  # 空队列;若 step2 调 LLM 会抛错
    library = [_fw("habit", ["习惯养成", "推送"]), _fw("pricing", ["定价"])]
    frameworks = steps.retrieve(_profile(), library, max_n=1)
    assert frameworks[0].id == "habit"
    assert provider.calls == []  # 确认未触 LLM


def test_step3_maps_each_feature():
    mapping = Mapping(
        feature="签到", framework_id="habit", principle_id="p",
        rationale="r", evidence="每日签到拿奖励", confidence=0.9,
    )
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[mapping]),
        MappingList(mappings=[]),  # 触点「推送」无映射
    ])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert mappings[0].feature == "签到"
    assert stats.kept == 1 and stats.dropped == 0


def test_step3_failure_marks_error_and_continues():
    # 队列耗尽 → 每个目标映射失败,应返回带 error 的占位 mapping 而非崩溃
    provider = FakeProvider(structured_responses=[])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert len(mappings) == 2  # 1 feature + 1 touchpoint
    assert all(m.error is not None for m in mappings)
    # 失败占位条目不参与溯源记账(spec §6)
    assert stats.kept == 0 and stats.dropped == 0


def test_step3_prompt_contains_source_and_quote_rules():
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[]), MappingList(mappings=[]),
    ])
    steps.map_features(provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    prompt = provider.calls[0]["prompt"]
    assert _DESC in prompt          # 产品原文全文必须进 step3(v8 及以前从未进过)
    assert "逐字复制" in prompt
    assert "宁可少给" in prompt


def test_step3_drops_ungrounded_evidence():
    good = Mapping(feature="签到", framework_id="habit", principle_id="p",
                   rationale="r", evidence="每日签到拿奖励", confidence=0.9)
    bad = Mapping(feature="签到", framework_id="habit", principle_id="p",
                  rationale="r", evidence="连续打卡显示徽章与排行榜", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[good, bad]), MappingList(mappings=[]),
    ])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert [m.evidence for m in mappings] == ["每日签到拿奖励"]
    assert stats.kept == 1 and stats.dropped == 1
    assert stats.dropped_mappings[0].evidence == "连续打卡显示徽章与排行榜"


def test_step3_overwrites_feature_with_target():
    # 实验实测:模型把 feature 写成「睡眠模块 - 连续睡眠打卡」这类 step1 从未
    # 产出的幽灵功能名。名字以调用目标为准,细分意图请模型写进 rationale。
    ghost = Mapping(feature="签到 - 连续签到打卡", framework_id="habit",
                    principle_id="p", rationale="r",
                    evidence="每日签到拿奖励", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[ghost]), MappingList(mappings=[]),
    ])
    mappings, _ = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert mappings[0].feature == "签到"


def test_step3_dropped_mapping_also_gets_target_feature():
    # 丢弃条目进附录,幽灵功能名同样要覆写,否则附录里全是模型自拼的名字
    bad = Mapping(feature="幽灵功能", framework_id="habit", principle_id="p",
                  rationale="r", evidence="原文里不存在的编造内容", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[bad]), MappingList(mappings=[]),
    ])
    _, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert stats.dropped_mappings[0].feature == "签到"


def test_step3_drops_evidence_below_min_quote_chars():
    # is_grounded 有长度下限(6 个归一化字符)。模型若只返回「签到」这类极短片段,
    # 即便是原文子串也必须丢弃,否则任何含「签到」二字的描述都能让该 mapping 通过。
    short = Mapping(feature="签到", framework_id="habit", principle_id="p",
                    rationale="r", evidence="签到", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[short]), MappingList(mappings=[]),
    ])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert mappings == []
    assert stats.dropped == 1


def test_step4_assess_experience():
    assessment = ExperienceAssessment(
        strengths=["强"], friction_points=["阻"], ethics_warnings=["伦"], opportunities=["机"],
    )
    provider = FakeProvider(structured_responses=[assessment])
    out = steps.assess_experience(provider, _profile(), [])
    assert out.strengths == ["强"]


def test_step5_synthesize():
    provider = FakeProvider(structured_responses=[Synthesis(executive_summary="总结文本")])
    summary = steps.synthesize(provider, _profile(), [], ExperienceAssessment())
    assert summary == "总结文本"
