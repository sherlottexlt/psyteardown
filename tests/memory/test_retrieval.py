import pytest

from psyteardown.embed.base import FakeEmbeddingProvider
from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore, MemoryStoreError
from psyteardown.memory.retrieval import search_similar, summarize_cases
from psyteardown.pipeline.schemas import (
    ProductProfile, ExperienceAssessment, TeardownResult, TeardownMeta,
)


def _result(name):
    return TeardownResult(
        product=ProductProfile(name=name, product_type="App",
                               one_liner=f"{name}的一句话", features=[], touchpoints=[]),
        frameworks_used=["hook-model"], mappings=[],
        assessment=ExperienceAssessment(), executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )


def _save(store, emb, desc, name):
    case = Case.from_result(_result(name), description=desc, created_at="t")
    store.save(case, emb.embed([desc])[0])
    return case


def test_empty_store_returns_empty(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    emb = FakeEmbeddingProvider()
    assert search_similar(store, emb, "随便查", top_k=3) == []


def test_most_similar_ranked_first(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    emb = FakeEmbeddingProvider()
    _save(store, emb, "签到打卡习惯养成推送提醒", "签到App")
    _save(store, emb, "股票基金理财投资收益", "理财App")
    hits = search_similar(store, emb, "签到打卡习惯养成", top_k=2)
    assert hits[0][0].product_name == "签到App"
    assert hits[0][1] >= hits[1][1]


def test_respects_top_k(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    emb = FakeEmbeddingProvider()
    for i in range(5):
        _save(store, emb, f"产品描述{i}", f"产品{i}")
    assert len(search_similar(store, emb, "产品描述0", top_k=2)) == 2


def test_dim_mismatch_raises(tmp_path):
    store = CaseStore(tmp_path / "c.db")
    _save(store, FakeEmbeddingProvider(dim=64), "产品A", "A")
    with pytest.raises(MemoryStoreError):
        search_similar(store, FakeEmbeddingProvider(dim=32), "产品A", top_k=1)


def test_summarize_cases_includes_name_and_frameworks():
    case = Case.from_result(_result("签到App"), description="d", created_at="t")
    text = summarize_cases([case])
    assert "签到App" in text
    assert "hook-model" in text


def test_summarize_empty_returns_empty_string():
    assert summarize_cases([]) == ""
