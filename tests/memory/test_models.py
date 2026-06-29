from psyteardown.memory.models import Case, case_id_for
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result():
    return TeardownResult(
        product=ProductProfile(name="Demo", product_type="App",
                               one_liner="每日签到App", features=[], touchpoints=[]),
        frameworks_used=["hook-model"],
        mappings=[],
        assessment=ExperienceAssessment(),
        executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="2026-06-14"),
    )


def test_case_id_is_deterministic_16_hex():
    a = case_id_for("每日签到App,有推送提醒")
    b = case_id_for("每日签到App,有推送提醒")
    assert a == b
    assert len(a) == 16
    assert case_id_for("别的产品") != a


def test_from_result_builds_case():
    case = Case.from_result(_result(), description="每日签到App描述", created_at="2026-06-14")
    assert case.case_id == case_id_for("每日签到App描述")
    assert case.product_name == "Demo"
    assert case.product_type == "App"
    assert case.one_liner == "每日签到App"
    assert case.frameworks_used == ["hook-model"]
    assert case.description == "每日签到App描述"
    assert case.result.executive_summary == "s"


def test_case_json_roundtrip():
    case = Case.from_result(_result(), description="d", created_at="t")
    again = Case.model_validate_json(case.model_dump_json())
    assert again.case_id == case.case_id
    assert again.result.product.name == "Demo"
