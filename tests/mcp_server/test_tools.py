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
