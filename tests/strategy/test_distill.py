from psyteardown.strategy.models import StrategyCard, CardList
from psyteardown.strategy.distill import distill_from_note
from psyteardown.llm.base import FakeProvider


def _card(id_, step="mapping"):
    return StrategyCard(id=id_, rule="社交产品别漏社交证明", rationale="人工复盘",
                        target_step=step, applies_to=["社交"])   # 无 source_case_ids


def test_empty_note_returns_empty():
    provider = FakeProvider()
    assert distill_from_note(provider, "  ", created_at="t") == []
    assert provider.calls == []


def test_note_in_prompt_and_stamps_created_at():
    card = _card("no-social-proof")
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = distill_from_note(provider, "社交产品别漏社交证明", created_at="2026-07-08")
    assert len(out) == 1
    assert out[0].created_at == "2026-07-08"
    assert "社交产品别漏社交证明" in provider.calls[0]["prompt"]


def test_keeps_card_without_source_cases():
    card = _card("x")
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    out = distill_from_note(provider, "note", created_at="t")
    assert out[0].source_case_ids == []      # 人工复盘豁免 min_support


def test_drops_invalid_target_step():
    card = _card("bad", step="synthesis")
    provider = FakeProvider(structured_responses=[CardList(cards=[card])])
    assert distill_from_note(provider, "note", created_at="t") == []
