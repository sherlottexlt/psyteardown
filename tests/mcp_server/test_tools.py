"""mcp_server.tools 单测:全离线(FakeProvider / FakeEmbeddingProvider)。"""

from pathlib import Path

from psyteardown.embed.base import FakeEmbeddingProvider
from psyteardown.mcp_server.tools import (
    AnalyzeOutcome, analyze_product, build_llm_provider,
)


def _fake_llm():
    return build_llm_provider("fake")


def _fake_embed_factory():
    return FakeEmbeddingProvider()


def test_analyze_product_returns_outcome(tmp_path):
    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="2026-07-17 12:00",
                        embed_factory=_fake_embed_factory)
    assert isinstance(o, AnalyzeOutcome)
    assert "# 心理学拆解报告" in o.rendered
    assert o.case_id is not None
    assert o.warnings == []


def test_analyze_product_no_save(tmp_path):
    from psyteardown.memory.store import CaseStore
    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="t", embed_factory=_fake_embed_factory,
                        no_save=True)
    assert o.case_id is None
    assert CaseStore(store).count() == 0


def test_analyze_product_embed_failure_degrades(tmp_path):
    def _boom():
        raise OSError("offline: 无法加载模型")

    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="t", embed_factory=_boom)
    assert "# 心理学拆解报告" in o.rendered          # 报告照常产出
    assert o.case_id is None                          # 未落盘
    assert any("记忆功能不可用" in w for w in o.warnings)


def test_analyze_product_self_review(tmp_path):
    store = tmp_path / "cases.db"
    o = analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                        store=store, now="t", embed_factory=_fake_embed_factory,
                        self_review=True)
    assert "拆解自评" in o.rendered


def test_teardown_tool_happy_path(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool
    store = tmp_path / "cases.db"
    out = teardown_tool("社交产品:动态推送点赞", store=store,
                        llm=_fake_llm(), embed_factory=_fake_embed_factory)
    assert "# 心理学拆解报告" in out
    assert "已落盘案例" in out


def test_teardown_tool_empty_description(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool
    out = teardown_tool("   ", store=tmp_path / "cases.db",
                        llm=_fake_llm(), embed_factory=_fake_embed_factory)
    assert out == "错误:输入为空。"


def test_teardown_tool_self_review(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool
    out = teardown_tool("社交产品:动态推送点赞", store=tmp_path / "cases.db",
                        llm=_fake_llm(), embed_factory=_fake_embed_factory,
                        self_review=True)
    assert "拆解自评" in out


def test_teardown_tool_degrades_with_warning_in_text(tmp_path):
    from psyteardown.mcp_server.tools import teardown_tool

    def _boom():
        raise OSError("offline")

    out = teardown_tool("社交产品:动态推送点赞", store=tmp_path / "cases.db",
                        llm=_fake_llm(), embed_factory=_boom)
    assert "# 心理学拆解报告" in out
    assert "记忆功能不可用" in out          # 警告并入返回文本
    assert "已落盘案例" not in out


def test_similar_tool_finds_seeded_case(tmp_path):
    from psyteardown.mcp_server.tools import similar_tool, teardown_tool
    store = tmp_path / "cases.db"
    teardown_tool("社交产品:动态推送点赞", store=store,
                  llm=_fake_llm(), embed_factory=_fake_embed_factory)
    out = similar_tool("社交产品:群组动态", store=store,
                       embed_factory=_fake_embed_factory)
    assert "样例产品" in out                  # fake LLM 的产品名


def test_similar_tool_empty_store(tmp_path):
    from psyteardown.mcp_server.tools import similar_tool
    out = similar_tool("任意描述", store=tmp_path / "empty.db",
                       embed_factory=_fake_embed_factory)
    assert "空" in out


def test_similar_tool_empty_description(tmp_path):
    from psyteardown.mcp_server.tools import similar_tool
    out = similar_tool(" ", store=tmp_path / "cases.db",
                       embed_factory=_fake_embed_factory)
    assert out == "错误:输入为空。"


def test_kb_list_tool_contains_seed(tmp_path):
    from psyteardown.mcp_server.tools import kb_list_tool
    out = kb_list_tool(store=tmp_path / "cases.db")
    assert "fogg-behavior-model" in out


def test_kb_show_tool_found_and_missing(tmp_path):
    from psyteardown.mcp_server.tools import kb_show_tool
    store = tmp_path / "cases.db"
    assert "心流" in kb_show_tool("flow", store=store)
    assert "未找到框架:nope" == kb_show_tool("nope", store=store)


def test_memory_stats_tool(tmp_path):
    from psyteardown.mcp_server.tools import memory_stats_tool, teardown_tool
    store = tmp_path / "cases.db"
    assert memory_stats_tool(store=store) == "案例数:0"
    teardown_tool("社交产品:动态推送点赞", store=store,
                  llm=_fake_llm(), embed_factory=_fake_embed_factory)
    assert memory_stats_tool(store=store) == "案例数:1"


def test_review_case_tool_backfills(tmp_path):
    from psyteardown.llm.base import FakeProvider
    from psyteardown.memory.store import CaseStore
    from psyteardown.review.models import CaseReview
    from psyteardown.mcp_server.tools import review_case_tool, teardown_tool

    store = tmp_path / "cases.db"
    teardown_tool("社交产品:动态推送点赞", store=store,
                  llm=_fake_llm(), embed_factory=_fake_embed_factory)
    cid = [c for c, _ in CaseStore(store).all()][0].case_id

    review_llm = FakeProvider(structured_responses=[
        CaseReview(score=0.4, weaknesses=["置信虚高"], suggestions=["核对数据"]),
    ])
    out = review_case_tool(cid, store=store, llm=review_llm)
    assert "总体评分 0.40" in out
    assert "置信虚高" in out
    assert CaseStore(store).get(cid).review.score == 0.4


def test_review_case_tool_missing(tmp_path):
    from psyteardown.mcp_server.tools import review_case_tool
    out = review_case_tool("nope", store=tmp_path / "cases.db", llm=_fake_llm())
    assert out == "案例不存在:nope"
