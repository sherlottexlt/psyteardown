import pytest

from psyteardown.growth.models import FrameworkCandidate
from psyteardown.growth.store import GrowthStore, GrowthError
from psyteardown.kb.models import Framework, Principle


def _cand(id_="dark-urgency"):
    fw = Framework(
        id=id_, name="虚假紧迫", category="persuasion", summary="制造人为时间压力。",
        tags=["紧迫"],
        principles=[Principle(id="p", name="倒计时", description="d", look_for=["倒计时"])],
        references=["r"],
    )
    return FrameworkCandidate(framework=fw, rationale="现有框架未覆盖",
                              source_case_ids=["a", "b", "c"], created_at="t")


def test_save_and_list(tmp_path):
    store = GrowthStore(tmp_path)
    assert store.list_candidates() == []
    store.save_candidate(_cand())
    cands = store.list_candidates()
    assert len(cands) == 1
    assert cands[0].framework.id == "dark-urgency"


def test_get_candidate(tmp_path):
    store = GrowthStore(tmp_path)
    store.save_candidate(_cand())
    assert store.get_candidate("dark-urgency").rationale == "现有框架未覆盖"
    assert store.get_candidate("nope") is None


def test_approve_moves_to_learned(tmp_path):
    store = GrowthStore(tmp_path)
    store.save_candidate(_cand())
    path = store.approve("dark-urgency")
    assert path.exists()
    assert path.parent == store.learned_dir()
    assert store.get_candidate("dark-urgency") is None      # 候选已删
    # learned 里只存 framework(与种子同构),可被 kb loader 读
    from psyteardown.kb.loader import load_frameworks
    fws = load_frameworks(learned_dir=store.learned_dir())
    assert any(f.id == "dark-urgency" for f in fws)


def test_reject_deletes(tmp_path):
    store = GrowthStore(tmp_path)
    store.save_candidate(_cand())
    store.reject("dark-urgency")
    assert store.get_candidate("dark-urgency") is None


def test_approve_missing_raises(tmp_path):
    store = GrowthStore(tmp_path)
    with pytest.raises(GrowthError):
        store.approve("nope")


def test_reject_missing_raises(tmp_path):
    store = GrowthStore(tmp_path)
    with pytest.raises(GrowthError):
        store.reject("nope")
