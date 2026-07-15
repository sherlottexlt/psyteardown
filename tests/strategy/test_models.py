from psyteardown.strategy.models import StrategyCard, CardList


def _card(id_="prefer-social-proof"):
    return StrategyCard(id=id_, rule="社交产品必查社交证明相关框架",
                        rationale="社交类案例中社交证明反复高置信命中",
                        target_step="retrieval", applies_to=["社交", "社区"],
                        source_case_ids=["a", "b", "c"], created_at="t")


def test_card_defaults():
    c = StrategyCard(id="x", rule="r", rationale="why", target_step="mapping")
    assert c.applies_to == []
    assert c.source_case_ids == []
    assert c.created_at == ""


def test_card_json_roundtrip():
    c = _card()
    again = StrategyCard.model_validate_json(c.model_dump_json())
    assert again.target_step == "retrieval"
    assert again.applies_to == ["社交", "社区"]


def test_card_list_wraps():
    assert CardList(cards=[]).cards == []
    assert CardList().cards == []
