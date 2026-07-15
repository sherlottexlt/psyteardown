from psyteardown.strategy.models import StrategyCard
from psyteardown.strategy.select import select_for
from psyteardown.pipeline.schemas import ProductProfile, Feature


def _profile(ptype="社交App", features=("动态",)):
    return ProductProfile(name="Demo", product_type=ptype, one_liner="x",
                          features=[Feature(name=f, description="d", user_goal="g") for f in features],
                          touchpoints=[])


def _card(id_, step, applies=()):
    return StrategyCard(id=id_, rule=f"规则{id_}", rationale="r",
                        target_step=step, applies_to=list(applies))


def test_empty_cards_returns_empty():
    assert select_for([], _profile(), "mapping") == ""


def test_mapping_step_selects_mapping_and_retrieval():
    cards = [_card("m", "mapping"), _card("r", "retrieval"), _card("a", "assessment")]
    out = select_for(cards, _profile(), "mapping")
    assert "规则m" in out
    assert "规则r" in out          # retrieval 并入 mapping
    assert "检索层建议" in out       # retrieval 标注
    assert "规则a" not in out       # assessment 不串台


def test_assessment_step_only_assessment():
    cards = [_card("m", "mapping"), _card("a", "assessment")]
    out = select_for(cards, _profile(), "assessment")
    assert "规则a" in out
    assert "规则m" not in out


def test_applies_to_wildcard_when_empty():
    cards = [_card("m", "mapping", applies=())]      # 空 = 通配
    assert "规则m" in select_for(cards, _profile(ptype="理财App"), "mapping")


def test_applies_to_hit_by_substring():
    cards = [_card("m", "mapping", applies=["社交"])]
    assert "规则m" in select_for(cards, _profile(ptype="社交App"), "mapping")


def test_applies_to_miss_excluded():
    cards = [_card("m", "mapping", applies=["理财"])]
    assert select_for(cards, _profile(ptype="社交App", features=("动态",)), "mapping") == ""
