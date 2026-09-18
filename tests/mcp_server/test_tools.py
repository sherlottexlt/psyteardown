"""mcp_server.tools 单测:全离线(FakeProvider / FakeEmbeddingProvider)。"""

import json
from datetime import datetime, timezone
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


def test_analyze_product_threads_max_n_to_retrieval(tmp_path, monkeypatch):
    """--max-n/--min-n 必须真的传到 run_teardown,而不是被静默吞掉。

    这是纯管道测试:v7 已把 max_n 透传到 retriever/steps/orchestrator 三层,
    但最外层(analyze_product / CLI)一直没暴露,导致调用方只能吃默认值
    (v7 spec §11 第二条记过这个口子)。
    """
    from psyteardown.mcp_server import tools

    seen = {}
    real = tools.run_teardown

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(tools, "run_teardown", spy)
    analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                    store=tmp_path / "cases.db", now="t",
                    embed_factory=_fake_embed_factory,
                    max_n=12, min_n=1)
    assert seen["max_n"] == 12
    assert seen["min_n"] == 1


def test_analyze_product_max_n_defaults_unchanged(tmp_path, monkeypatch):
    """默认值仍是 v7 的 8/5 —— 新增选项不得改变既有行为。"""
    from psyteardown.mcp_server import tools

    seen = {}
    real = tools.run_teardown
    monkeypatch.setattr(tools, "run_teardown",
                        lambda *a, **k: (seen.update(k), real(*a, **k))[1])
    analyze_product(_fake_llm(), "社交产品:动态推送点赞",
                    store=tmp_path / "cases.db", now="t",
                    embed_factory=_fake_embed_factory)
    assert seen["max_n"] == 8
    assert seen["min_n"] == 5


def _seed_engineering_project(database: Path) -> None:
    from psyteardown.experience import (
        EngineeringOrchestrator,
        EngineeringProjectRevision,
        EngineeringRequirement,
        RevisionMeta,
        SQLiteExperienceRepository,
        VerificationTestRun,
        dependency_ref,
    )

    reviewed_at = datetime(2026, 9, 17, tzinfo=timezone.utc)
    with SQLiteExperienceRepository(database) as repository:
        registry = EngineeringOrchestrator(repository)
        requirement = registry.register("requirement", EngineeringRequirement(
            requirement_id="mcp-cancel",
            revision_id="mcp-cancel.r1",
            meta=RevisionMeta(
                revision=1,
                created_by="system-engineer-li",
                reason="reviewed requirement",
            ),
            status="approved",
            reviewer="system-engineer-li",
            reviewed_at=reviewed_at,
            title="explicit cancellation",
            requirement_type="must",
            hard_constraint=True,
            source_type="user_declared",
            source_refs=("owner interview",),
            acceptance_criteria=("instrumented test confirms cancellation",),
            verification_methods=("physical task test",),
        ))
        registry.register("verification_test", VerificationTestRun(
            test_run_id="mcp-cancel-test",
            revision_id="mcp-cancel-test.r1",
            meta=RevisionMeta(
                revision=1,
                created_by="test-lead",
                reason="physical result reviewed",
            ),
            status="approved",
            reviewer="test-lead",
            reviewed_at=reviewed_at,
            protocol_id="cancel-protocol.r1",
            test_type="physical task test",
            sample_ids=("prototype-1",),
            raw_measurement_refs=("cancel.csv#sha256:a",),
            result="pass",
            evidence_review_id="evidence-review.r1",
            dependencies=(dependency_ref("requirement", requirement.requirement_id, 1),),
        ))
        registry.register("project", EngineeringProjectRevision(
            project_id="mcp-project",
            revision_id="mcp-project.r1",
            meta=RevisionMeta(
                revision=1,
                created_by="system-engineer-li",
                reason="project snapshot",
            ),
            intake_revision_id="mcp-intake.r1",
            scenario="walking transit",
            product_purpose="bounded cancellation",
            requirement_revision_ids=(requirement.revision_id,),
            dependencies=(dependency_ref("requirement", requirement.requirement_id, 1),),
        ))


def test_engineering_status_tool_is_read_only_projection(tmp_path):
    from psyteardown.mcp_server.tools import engineering_status_tool

    database = tmp_path / "experience.db"
    _seed_engineering_project(database)
    payload = json.loads(engineering_status_tool("mcp-project", store=database))
    assert payload["project"]["project_id"] == "mcp-project"
    assert payload["requirements"][0]["status"] == "approved"
    assert payload["stale_objects"] == []
    assert "no AI or MCP call can approve" in payload["boundary"]


def test_engineering_traceability_tool_renders_both_formats(tmp_path):
    from psyteardown.mcp_server.tools import engineering_traceability_tool

    database = tmp_path / "experience.db"
    _seed_engineering_project(database)
    markdown = engineering_traceability_tool("mcp-project", store=database)
    assert "# Engineering Traceability" in markdown
    assert "`traceable`" in markdown
    payload = json.loads(
        engineering_traceability_tool("mcp-project", store=database, fmt="json")
    )
    assert payload["status"] == "traceable"


def test_engineering_mcp_tools_report_invalid_input_without_mutation(tmp_path):
    from psyteardown.mcp_server.tools import (
        engineering_status_tool,
        engineering_traceability_tool,
    )

    database = tmp_path / "empty.db"
    assert engineering_status_tool(" ", store=database).startswith("错误:")
    assert engineering_status_tool("missing", store=database) == "工程项目不存在:missing"
    assert engineering_traceability_tool(
        "missing", store=database, fmt="yaml"
    ).startswith("错误:format")
