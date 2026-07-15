import pytest

from psyteardown.strategy.models import StrategyCard
from psyteardown.strategy.store import StrategyStore, StrategyError


def _card(id_="prefer-social-proof"):
    return StrategyCard(id=id_, rule="社交产品必查社交证明", rationale="why",
                        target_step="retrieval", applies_to=["社交"],
                        source_case_ids=["a", "b", "c"], created_at="t")


def test_save_and_list(tmp_path):
    store = StrategyStore(tmp_path)
    assert store.list_candidates() == []
    store.save_candidate(_card())
    cards = store.list_candidates()
    assert len(cards) == 1
    assert cards[0].id == "prefer-social-proof"


def test_get_candidate(tmp_path):
    store = StrategyStore(tmp_path)
    store.save_candidate(_card())
    assert store.get_candidate("prefer-social-proof").rule == "社交产品必查社交证明"
    assert store.get_candidate("nope") is None


def test_approve_moves_to_approved(tmp_path):
    store = StrategyStore(tmp_path)
    store.save_candidate(_card())
    path = store.approve("prefer-social-proof")
    assert path.exists()
    assert path.parent == store.approved_dir()
    assert store.get_candidate("prefer-social-proof") is None      # 候选已删
    approved = store.list_approved()
    assert [c.id for c in approved] == ["prefer-social-proof"]


def test_reject_records_and_save_skips(tmp_path):
    store = StrategyStore(tmp_path)
    store.save_candidate(_card())
    store.reject("prefer-social-proof")
    assert store.is_rejected("prefer-social-proof")
    store.save_candidate(_card())                                  # 同 id 不复活
    assert store.get_candidate("prefer-social-proof") is None


def test_invalid_id_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.save_candidate(_card("../evil"))


def test_get_candidate_invalid_id_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.get_candidate("../../etc/passwd")


def test_approve_missing_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.approve("nope")


def test_reject_missing_raises(tmp_path):
    store = StrategyStore(tmp_path)
    with pytest.raises(StrategyError):
        store.reject("nope")
