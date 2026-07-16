import pytest

from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result(name="Demo"):
    return TeardownResult(
        product=ProductProfile(name=name, product_type="App",
                               one_liner="x", features=[], touchpoints=[]),
        frameworks_used=["hook-model"], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def _case(desc, name="Demo"):
    return Case.from_result(_result(name), description=desc, created_at="t")


def test_save_and_count(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    assert store.count() == 0
    store.save(_case("产品A"), [0.1, 0.2, 0.3])
    assert store.count() == 1


def test_get_returns_case(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    case = _case("产品A")
    store.save(case, [0.1, 0.2, 0.3])
    got = store.get(case.case_id)
    assert got is not None
    assert got.product_name == "Demo"
    assert got.description == "产品A"


def test_get_missing_returns_none(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    assert store.get("deadbeefdeadbeef") is None


def test_upsert_same_description_no_duplicate(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    store.save(_case("产品A", name="旧名"), [0.1, 0.2, 0.3])
    store.save(_case("产品A", name="新名"), [0.4, 0.5, 0.6])  # 同描述 → 同 id → 覆盖
    assert store.count() == 1
    assert store.get(_case("产品A").case_id).product_name == "新名"


def test_all_roundtrips_case_and_vector(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    store.save(_case("产品A"), [0.1, 0.2, 0.3])
    rows = store.all()
    assert len(rows) == 1
    case, vec = rows[0]
    assert case.description == "产品A"
    assert len(vec) == 3
    assert abs(vec[0] - 0.1) < 1e-6


def test_creates_parent_dir(tmp_path):
    store = CaseStore(tmp_path / "nested" / "dir" / "cases.db")
    store.save(_case("产品A"), [0.1])
    assert (tmp_path / "nested" / "dir" / "cases.db").exists()


def test_get_with_embedding_hit(tmp_path):
    case = _case("产品A")
    store = CaseStore(tmp_path / "cases.db")
    store.save(case, [0.1, 0.2, 0.3])

    hit = store.get_with_embedding(case.case_id)
    assert hit is not None
    got_case, vec = hit
    assert got_case.case_id == case.case_id
    assert len(vec) == 3
    assert abs(vec[1] - 0.2) < 1e-6           # float32 往返有精度损失


def test_get_with_embedding_missing(tmp_path):
    store = CaseStore(tmp_path / "cases.db")
    assert store.get_with_embedding("nope") is None
