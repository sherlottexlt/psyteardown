"""薄 CLI:读输入 → 调内核 → 写输出。零业务逻辑。"""

import json
from datetime import datetime
from pathlib import Path

import typer

from psyteardown.kb.loader import load_frameworks
from psyteardown.embed.base import EmbeddingProvider
from psyteardown.memory.store import CaseStore
from psyteardown.memory.retrieval import search_similar
from psyteardown.review.critic import review_case
from psyteardown.growth.store import GrowthStore
from psyteardown.growth.proposer import propose_frameworks
from psyteardown.growth.dedup import filter_duplicates
from psyteardown.strategy.store import StrategyStore
from psyteardown.strategy.proposer import propose_strategies
from psyteardown.strategy.distill import distill_from_note
from psyteardown.mcp_server.tools import (
    DEFAULT_STORE,
    analyze_product,
    build_embed_provider as _build_embed_provider,
    build_llm_provider as _build_provider,
)
from psyteardown.experience import (
    BlenderDesignToolProvider,
    BlenderProviderError,
    DesignToolResult,
    FakeDesignToolProvider,
    ExperienceApplicationService,
    SQLiteExperienceRepository,
    InitialDesignRequest,
    ProgressiveDesignModel,
    VariablePatch,
    PrototypeRun,
    MeasurementObservation,
    ExternalAsset,
    ObservationDraft,
    DomainStateError,
    build_scenario_policy,
    build_portfolio_case_study,
    build_design_tool_request,
    default_transit_validation_protocol,
    VirtualValidationInput,
    VirtualValidationReport,
    render_virtual_validation_markdown,
    run_virtual_validation,
    ScenarioReplayInput,
    render_scenario_replay_markdown,
    run_scenario_replay,
    ScenarioReplayReport,
    generate_initial_design_batch,
    render_candidate_json,
    render_candidate_markdown,
    render_progressive_model_markdown,
    render_initial_design_batch,
    render_initial_design_json,
    render_portfolio_markdown,
    Evidence,
    Observation,
    ExperienceHypothesis,
    Critique,
    ExperimentPlan,
    ExperimentVariable,
    MeasureSpec,
    SamplePlan,
    StoppingRule,
    DesignBrief,
    DesignCandidate,
    ResearchApplicationService,
    render_research_json,
    render_research_markdown,
    build_experiment_plan,
    preregister_plan,
    render_experiment_plan_json,
    render_experiment_plan_markdown,
    run_feedback_loop,
    select_feedback_candidate,
    build_feedback_selection,
    render_feedback_json,
    render_feedback_markdown,
    ScaffoldDesignGenerator,
)
from psyteardown.experience.repositories import RepositoryError

app = typer.Typer(help="psyteardown 体验假设与验证 Agent")
kb_app = typer.Typer(help="知识库操作")
memory_app = typer.Typer(help="案例库操作")
candidates_app = typer.Typer(help="习得框架候选:审阅/批准/驳回")
strategies_app = typer.Typer(help="拆解策略卡:审阅/批准/驳回")
app.add_typer(kb_app, name="kb")
app.add_typer(memory_app, name="memory")
app.add_typer(candidates_app, name="candidates")
app.add_typer(strategies_app, name="strategies")


@app.command("design-feedback")
def design_feedback(
    brief: Path = typer.Option(..., "--brief", "-i", help="DesignBrief JSON 文件"),
    db: Path = typer.Option(Path("output/experience/experience.sqlite3"), "--db", help="SQLite 数据库"),
    count: int = typer.Option(5, "--count", "-n", help="候选数量"),
    out: Path | None = typer.Option(None, "--out", "-o", help="机器可读反馈 JSON"),
    fmt: str = typer.Option("json", "--format", "-f", help="json 或 md"),
):
    """运行 M3 generate → critique → rank → next-prompt 最小闭环。"""
    try:
        if fmt not in {"json", "md"}:
            raise ValueError("--format 只能是 json 或 md")
        source = DesignBrief.model_validate_json(brief.read_text(encoding="utf-8"))
        result = run_feedback_loop(source, generator=ScaffoldDesignGenerator(), n=count)
        with SQLiteExperienceRepository(db) as repository:
            if repository.get_revision("brief", source.revision_id) is None:
                repository.save("brief", source.brief_id, source.revision_id, source)
            for candidate in result.candidates:
                repository.save("candidate", candidate.candidate_id, candidate.candidate_revision_id, candidate)
            for critique in result.critiques:
                repository.save("critique", critique.critique_id, critique.revision_id, critique)
        rendered = render_feedback_json(result) if fmt == "json" else render_feedback_markdown(result)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
            typer.echo(f"已写入 {out}")
        else:
            typer.echo(rendered)
    except (OSError, ValueError, json.JSONDecodeError, RepositoryError) as exc:
        typer.echo(f"错误:无法运行设计反馈闭环: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("design-feedback-select")
def design_feedback_select(
    brief: Path = typer.Option(..., "--brief", "-i", help="DesignBrief JSON 文件"),
    feedback: Path = typer.Option(..., "--feedback", help="design-feedback 导出的 JSON"),
    db: Path = typer.Option(Path("output/experience/experience.sqlite3"), "--db", help="SQLite 数据库"),
    candidate_id: str = typer.Option(..., "--candidate", help="人工选择的 candidate ID"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出更新后的反馈 JSON"),
):
    """人工选择候选并生成下一轮设计 prompt。"""
    try:
        source = DesignBrief.model_validate_json(brief.read_text(encoding="utf-8"))
        payload = json.loads(feedback.read_text(encoding="utf-8"))
        candidates = tuple(DesignCandidate.model_validate(item) for item in payload.get("candidates", []))
        critiques = tuple(Critique.model_validate(item) for item in payload.get("critiques", []))
        result = type("Feedback", (), {})()
        from psyteardown.experience.m3_feedback import DesignFeedbackResult
        result = DesignFeedbackResult(
            brief_revision_id=payload["brief_revision_id"],
            iteration_id=payload.get("iteration_id"),
            candidate_ids=tuple(payload.get("candidate_ids", ())),
            critique_ids=tuple(payload.get("critique_ids", ())),
            ranked_candidate_ids=tuple(payload.get("ranked_candidate_ids", ())),
            selected_candidate_id=payload.get("selected_candidate_id"),
            next_prompt=None,
            critiques=critiques,
            candidates=candidates,
        )
        updated = select_feedback_candidate(source, result, candidate_id)
        selection = build_feedback_selection(updated)
        with SQLiteExperienceRepository(db) as repository:
            for candidate in updated.candidates:
                if repository.get_revision("candidate", candidate.candidate_revision_id) is None:
                    repository.save("candidate", candidate.candidate_id, candidate.candidate_revision_id, candidate)
            for critique in updated.critiques:
                if repository.get_revision("critique", critique.revision_id) is None:
                    repository.save("critique", critique.critique_id, critique.revision_id, critique)
            if repository.get_revision("feedback_selection", selection.revision_id) is None:
                repository.save("feedback_selection", selection.selection_id, selection.revision_id, selection)
        rendered = render_feedback_json(updated)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
            typer.echo(f"已写入 {out}")
        else:
            typer.echo(rendered)
    except (OSError, ValueError, json.JSONDecodeError, RepositoryError) as exc:
        typer.echo(f"错误:无法确认设计候选: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("experiment-plan")
def experiment_plan(
    hypothesis: Path = typer.Option(..., "--hypothesis", "-i", help="ExperienceHypothesis JSON 文件"),
    db: Path = typer.Option(Path("output/experience/experience.sqlite3"), "--db", help="SQLite 数据库"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出计划；省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
):
    """从条件性体验假设生成 M2 实验规划草案。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        value = json.loads(hypothesis.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "hypothesis" in value:
            value = value["hypothesis"]
        elif isinstance(value, dict) and isinstance(value.get("hypotheses"), list):
            if not value["hypotheses"]:
                raise ValueError("research JSON 中没有 hypotheses")
            value = value["hypotheses"][0]
        source = ExperienceHypothesis.model_validate(value)
        plan = build_experiment_plan(source, brief_revision_id=value.get("brief_revision_id", "unbound-brief.r1") if isinstance(value, dict) else "unbound-brief.r1")
        with SQLiteExperienceRepository(db) as repository:
            repository.save("experiment_plan", plan.experiment_id, plan.revision_id, plan)
        rendered = render_experiment_plan_json(plan) if fmt == "json" else render_experiment_plan_markdown(plan)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
            typer.echo(f"已写入 {out}")
        else:
            typer.echo(rendered)
    except (OSError, ValueError, json.JSONDecodeError, RepositoryError) as exc:
        typer.echo(f"错误:无法生成实验规划: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("experiment-preregister")
def experiment_preregister(
    input: Path = typer.Option(..., "--input", "-i", help="ExperimentPlan JSON 文件或数据库中的 experiment_id"),
    db: Path = typer.Option(Path("output/experience/experience.sqlite3"), "--db", help="SQLite 数据库"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出计划；省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    actor: str = typer.Option("human", "--actor", help="人工审批者"),
):
    """人工确认完整实验计划，创建不可变 preregistered revision。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        raw = input.read_text(encoding="utf-8") if input.exists() else None
        with SQLiteExperienceRepository(db) as repository:
            if raw is not None:
                plan = ExperimentPlan.model_validate_json(raw)
            else:
                revisions = repository.list_revisions("experiment_plan", input.name)
                if not revisions:
                    raise ValueError(f"实验规划不存在: {input.name}")
                plan = revisions[-1]
            updated = preregister_plan(plan, actor=actor)
            repository.save("experiment_plan", updated.experiment_id, updated.revision_id, updated)
        rendered = render_experiment_plan_json(updated) if fmt == "json" else render_experiment_plan_markdown(updated)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
            typer.echo(f"已写入 {out}")
        else:
            typer.echo(rendered)
    except (OSError, ValueError, json.JSONDecodeError, RepositoryError) as exc:
        typer.echo(f"错误:无法预注册实验规划: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("research-import")
def research_import(
    input: Path = typer.Option(..., "--input", "-i", help="M1 research JSON 文件"),
    db: Path = typer.Option(Path("output/experience/experience.sqlite3"), "--db", help="SQLite 数据库"),
):
    """导入通用 Evidence/Observation/Hypothesis/Critique（仅保存可追溯草案）。"""
    try:
        payload = json.loads(input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("research JSON 必须是对象")
        _reject_template_payload(payload, source=input)
        with SQLiteExperienceRepository(db) as repository:
            service = ResearchApplicationService(repository)
            counts = {}
            for key, model, saver in (
                ("evidence", Evidence, service.save_evidence),
                ("observations", Observation, service.save_observation),
                ("hypotheses", ExperienceHypothesis, service.save_hypothesis),
                ("critiques", Critique, service.save_critique),
            ):
                raw = payload.get(key, [])
                if isinstance(raw, dict):
                    raw = [raw]
                if not isinstance(raw, list):
                    raise ValueError(f"{key} 必须是数组")
                counts[key] = 0
                for value in raw:
                    saver(model.model_validate(value))
                    counts[key] += 1
        typer.echo(json.dumps({"imported": counts}, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError, RepositoryError) as exc:
        typer.echo(f"错误:无法导入 research 数据: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("research-export")
def research_export(
    db: Path = typer.Option(Path("output/experience/experience.sqlite3"), "--db", help="SQLite 数据库"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出文件；省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
):
    """导出通用研究对象；未确认内容不会被提升为支持性结论。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        with SQLiteExperienceRepository(db) as repository:
            values = {
                "evidence": repository.list_revisions("evidence"),
                "observations": repository.list_revisions("observation"),
                "hypotheses": repository.list_revisions("experience_hypothesis"),
                "critiques": repository.list_revisions("critique"),
            }
        rendered = render_research_json(**values) if fmt == "json" else render_research_markdown(**values)
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rendered, encoding="utf-8")
            typer.echo(f"已写入 {out}")
        else:
            typer.echo(rendered)
    except (OSError, ValueError, RepositoryError) as exc:
        typer.echo(f"错误:无法导出 research 数据: {exc}", err=True)
        raise typer.Exit(code=1)


_TEMPLATE_MARKERS = ("REPLACE_ME", "YYYYMMDD")


def _reject_template_payload(payload: object, *, source: Path) -> None:
    """Prevent the handoff templates from being imported as if they were data.

    The physical-prototype templates intentionally contain sentinel values.  A
    successful Pydantic parse is not sufficient evidence that a run is real;
    importing one of those files would create misleading draft provenance in
    the case database.  Keep this guard at the CLI boundary so the domain
    service remains usable for legitimate synthetic/test fixtures.
    """

    def walk(value: object, path: str) -> tuple[str, str] | None:
        if isinstance(value, dict):
            for key, child in value.items():
                found = walk(child, f"{path}.{key}")
                if found:
                    return found
        elif isinstance(value, list):
            for index, child in enumerate(value):
                found = walk(child, f"{path}[{index}]")
                if found:
                    return found
        elif isinstance(value, str):
            for marker in _TEMPLATE_MARKERS:
                if marker in value:
                    return path, marker
        return None

    found = walk(payload, "$")
    if found:
        path, marker = found
        raise ValueError(
            f"{source} still contains template placeholder {marker!r} at {path}; "
            "fill the real prototype run/measurement values before import"
        )


def _known_prototype_protocol(run: PrototypeRun):
    """Return the frozen built-in protocol for the transit-anchor workflow.

    Custom protocols can still be imported when their run carries an explicit
    protocol snapshot.  The known transit protocol is bound automatically so
    its measure IDs are snapshotted and observation imports cannot silently
    bypass the preregistered measure list.
    """

    protocol = default_transit_validation_protocol()
    if run.protocol_id == protocol.protocol_id and run.protocol_revision == protocol.protocol_revision:
        return protocol
    return None


@app.command("virtual-validate")
def virtual_validate(
    input: Path = typer.Option(..., "--input", "-i", help="VirtualValidationInput JSON 文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出报告；省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
):
    """运行一阶物理预检；结果永远不是样机证据。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        spec = VirtualValidationInput.model_validate_json(input.read_text(encoding="utf-8"))
        report = run_virtual_validation(spec)
        rendered = render_virtual_validation_markdown(report) if fmt == "md" else report.model_dump_json(indent=2)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"错误:无法运行虚拟工程预检: {exc}", err=True)
        raise typer.Exit(code=1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@app.command("scenario-replay")
def scenario_replay(
    policy: Path = typer.Option(..., "--policy", help="ScenarioPolicy JSON 文件"),
    input: Path = typer.Option(..., "--input", "-i", help="ScenarioReplayInput JSON 文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出轨迹报告；省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
):
    """演练 routine 状态机；只验证策略控制流，不产生用户证据。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        from psyteardown.experience import ScenarioPolicy

        policy_object = ScenarioPolicy.model_validate_json(policy.read_text(encoding="utf-8"))
        spec = ScenarioReplayInput.model_validate_json(input.read_text(encoding="utf-8"))
        report = run_scenario_replay(policy_object, spec)
        rendered = render_scenario_replay_markdown(report) if fmt == "md" else report.model_dump_json(indent=2)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"错误:无法运行场景策略演练: {exc}", err=True)
        raise typer.Exit(code=1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@app.command("prototype-import")
def import_prototype_evidence(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    run: Path = typer.Option(..., "--run", help="PrototypeRun JSON 文件"),
    observations: Path | None = typer.Option(None, "--observations", help="MeasurementObservation 数组 JSON 文件"),
):
    """导入样机运行与原始测量；导入永远保持 draft，不产生 evidence。"""
    try:
        run_payload = json.loads(run.read_text(encoding="utf-8"))
        _reject_template_payload(run_payload, source=run)
        run_object = PrototypeRun.model_validate(run_payload)
        payload = []
        if observations:
            raw = json.loads(observations.read_text(encoding="utf-8"))
            _reject_template_payload(raw, source=observations)
            payload = raw.get("observations", raw) if isinstance(raw, dict) else raw
            if not isinstance(payload, list):
                raise ValueError("observations JSON 必须是数组或包含 observations 数组的对象")
        observation_objects = tuple(MeasurementObservation.model_validate(item) for item in payload)
        protocol = _known_prototype_protocol(run_object)
        if protocol is not None:
            registered_measures = {item.measure_id for item in protocol.measures}
            unknown_measures = sorted({item.measure_id for item in observation_objects} - registered_measures)
            if unknown_measures:
                raise ValueError(
                    "observations contain measure IDs outside the preregistered protocol: "
                    + ", ".join(unknown_measures)
                )
        if any(item.condition not in run_object.conditions for item in observation_objects):
            invalid_conditions = sorted({item.condition for item in observation_objects if item.condition not in run_object.conditions})
            raise ValueError(
                "observations contain conditions not declared by the prototype run: "
                + ", ".join(invalid_conditions)
            )
        observation_ids = [item.observation_id for item in observation_objects]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("observations must use a unique observation_id per measurement")
        registered_asset_ids = {asset.asset_id for asset in run_object.source_assets}
        unregistered_assets = sorted({asset_id for item in observation_objects for asset_id in item.source_asset_ids} - registered_asset_ids)
        if unregistered_assets:
            raise ValueError(
                "observations reference assets not registered on the prototype run: "
                + ", ".join(unregistered_assets)
            )
        with SQLiteExperienceRepository(db) as repository:
            if repository.get_revision("prototype_run", run_object.revision_id) is not None:
                raise ValueError(f"prototype run revision already imported: {run_object.revision_id}")
            conflicting_assets = [
                asset.asset_id
                for asset in run_object.source_assets
                if (
                    (existing := repository.get_revision("prototype_asset", asset.asset_id)) is not None
                    and (existing.sha256 != asset.sha256 or existing.uri != asset.uri)
                )
            ]
            if conflicting_assets:
                raise ValueError(
                    "prototype asset IDs already name different files: "
                    + ", ".join(conflicting_assets)
                )
            duplicate_observations = [
                item.revision_id
                for item in observation_objects
                if repository.get_revision("measurement_observation", item.revision_id) is not None
            ]
            if duplicate_observations:
                raise ValueError(
                    "measurement observation revisions already imported: "
                    + ", ".join(duplicate_observations)
                )
            service = ExperienceApplicationService(repository)
            service.import_prototype_run(run_object, protocol=protocol, require_lineage=True)
            imported = service.import_measurement_observations(
                run_object,
                observation_objects,
            )
            typer.echo(json.dumps({"run_id": run_object.run_id, "observation_ids": [item.observation_id for item in imported], "evidence_level": "none"}, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法导入样机证据: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("prototype-review")
def review_prototype_evidence(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    run_id: str = typer.Option(..., "--run-id"),
    observation: list[str] = typer.Option([], "--observation", help="人工确认的 observation ID，可重复"),
    decision: str = typer.Option("accepted", "--decision"),
    evidence_level: str = typer.Option("observed", "--evidence-level"),
    reviewer: str = typer.Option("human", "--reviewer"),
    rationale: str = typer.Option("human evidence review", "--rationale"),
):
    """记录人工 EvidenceReview；Blender 派生观测不可确认。"""
    try:
        with SQLiteExperienceRepository(db) as repository:
            run_object = repository.get_current("prototype_run", run_id)
            if run_object is None:
                raise ValueError(f"prototype run 不存在: {run_id}")
            review = ExperienceApplicationService(repository).review_evidence(
                run_object,
                decision=decision,
                reviewer=reviewer,
                evidence_level_after=evidence_level,
                confirmed_observation_ids=observation,
                rationale=rationale,
            )
            typer.echo(review.model_dump_json(indent=2))
    except (OSError, ValueError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法记录证据复核: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("scenario-policy")
def export_scenario_policy(
    input: Path = typer.Option(..., "--input", "-i", help="FutureMovementScenario JSON 文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出 ScenarioPolicy JSON"),
    freeze: bool = typer.Option(False, "--freeze", help="将策略标为 frozen；仍只代表人工可审阅的确定性政策，不代表传感器验证"),
):
    """将声明的 movement scenario 编译为可执行的 routine policy。"""
    try:
        from psyteardown.experience import FutureMovementScenario
        scenario = FutureMovementScenario.model_validate_json(input.read_text(encoding="utf-8"))
        policy = build_scenario_policy(scenario, status="frozen" if freeze else "candidate")
        rendered = policy.model_dump_json(indent=2)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"错误:无法编译场景策略: {exc}", err=True)
        raise typer.Exit(code=1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@app.command("asset-import")
def import_external_asset(
    db: Path = typer.Option(..., "--db"),
    input: Path = typer.Option(..., "--input", "-i", help="ExternalAsset JSON 文件"),
):
    """导入外部 GLB/PNG/CAD 资产；只记录 hash 与来源，不生成事实。"""
    try:
        asset = ExternalAsset.model_validate_json(input.read_text(encoding="utf-8"))
        with SQLiteExperienceRepository(db) as repository:
            imported = ExperienceApplicationService(repository).import_external_asset(asset)
            typer.echo(imported.model_dump_json(indent=2))
    except (OSError, ValueError, json.JSONDecodeError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法导入外部资产: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("observation-draft-review")
def review_observation_draft(
    db: Path = typer.Option(..., "--db"),
    input: Path = typer.Option(..., "--input", "-i", help="ObservationDraft JSON 文件"),
    decision: str = typer.Option("accepted", "--decision"),
    value: str | None = typer.Option(None, "--value"),
):
    """人工确认外部资产观察草案；仅产生 design fact observation。"""
    try:
        draft = ObservationDraft.model_validate_json(input.read_text(encoding="utf-8"))
        with SQLiteExperienceRepository(db) as repository:
            result = ExperienceApplicationService(repository).review_observation_draft(draft, decision=decision, value=value)
            typer.echo(result.model_dump_json(indent=2))
    except (OSError, ValueError, json.JSONDecodeError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法复核观察草案: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("design")
def generate_design(
    input: Path = typer.Option(..., "--input", "-i", help="结构化产品设计请求 JSON 文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出文件；省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    variant: int | None = typer.Option(None, "--variant", min=0, help="输出单个候选的 0-based 变体索引；省略输出 5 个候选"),
    db: Path | None = typer.Option(None, "--db", help="可选：把 Brief、Iteration、Candidates 和事件写入 experience SQLite"),
):
    """根据结构化 DesignBrief 请求生成完整的初步产品设计。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        request = InitialDesignRequest.model_validate_json(input.read_text(encoding="utf-8"))
        if db is None:
            batch = generate_initial_design_batch(request)
        else:
            with SQLiteExperienceRepository(db) as repository:
                batch = generate_initial_design_batch(request, repository=repository)
        if variant is None:
            rendered = render_initial_design_batch(batch) if fmt == "md" else render_initial_design_json(batch)
        else:
            try:
                candidate = batch.candidates[variant]
            except IndexError as exc:
                raise ValueError(f"variant must be between 0 and {len(batch.candidates) - 1}") from exc
            rendered = render_candidate_markdown(candidate) if fmt == "md" else render_candidate_json(candidate)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"错误:设计请求无效或无法读取: {exc}", err=True)
        raise typer.Exit(code=1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@app.command("design-attach")
def attach_design_tool(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    candidate_revision: str = typer.Option(..., "--candidate-revision", help="候选 revision ID"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出 progressive model 文件"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    confirm: bool = typer.Option(False, "--confirm", help="人工确认 provider 草案并推进模型层级"),
    result_file: Path | None = typer.Option(None, "--result", help="外部设计工具返回的 DesignToolResult JSON；省略则使用 Fake provider"),
    provider: str = typer.Option("fake", "--provider", help="fake 或 blender"),
    blender_executable: Path | None = typer.Option(None, "--blender-executable", help="Blender 可执行文件路径；省略则读取 PSYTEARDOWN_BLENDER 或 PATH"),
    blender_output_root: Path = typer.Option("output/experience/blender", "--blender-output-root", help="Blender 派生资产输出目录"),
):
    """接收 Fake/外部设计工具结果，并记录草案或确认后的模型 revision。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        with SQLiteExperienceRepository(db) as repository:
            candidate = repository.get_revision("candidate", candidate_revision)
            if candidate is None:
                raise ValueError(f"候选 revision 不存在: {candidate_revision}")
            rule_sets = [
                value
                for value in repository.list_revisions("rule_set")
                if value.brief_revision_id == candidate.brief_revision_id
            ]
            if not rule_sets:
                raise ValueError("candidate 没有关联 DesignRuleSet")
            models = [
                value
                for value in repository.list_revisions("progressive_model")
                if value.candidate_revision_id == candidate_revision
            ]
            if not models:
                raise ValueError("candidate 没有关联 ProgressiveDesignModel")
            model = max(models, key=lambda value: value.meta.revision)
            request = build_design_tool_request(candidate, rule_sets[-1], parent_model_revision_id=model.revision_id)
            if result_file is None:
                if provider == "fake":
                    result = FakeDesignToolProvider().generate(request)
                elif provider == "blender":
                    result = BlenderDesignToolProvider(
                        blender_executable,
                        output_root=blender_output_root,
                    ).generate(request)
                else:
                    raise ValueError("--provider 只能是 fake 或 blender")
            else:
                result = DesignToolResult.model_validate_json(result_file.read_text(encoding="utf-8"))
                if result.request_id != request.request_id:
                    raise ValueError(
                        "DesignToolResult.request_id 与当前导出的请求不匹配；请使用同一 candidate revision 的 request/result"
                    )
            updated = ExperienceApplicationService(repository).attach_design_tool_result(
                model,
                result,
                confirmed=confirm,
                actor="human" if confirm else "system",
                request=request,
            )
            rendered = render_progressive_model_markdown(updated) if fmt == "md" else updated.model_dump_json(indent=2)
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(rendered, encoding="utf-8")
                typer.echo(f"已写入 {out}")
            else:
                typer.echo(rendered)
    except (OSError, ValueError, DomainStateError, BlenderProviderError, RepositoryError) as exc:
        typer.echo(f"错误:无法推进设计模型: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("design-review")
def review_design_tool_run(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    run_id: str = typer.Option(..., "--run-id", help="待确认的 DesignToolRun aggregate ID"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出 progressive model 文件"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    reviewer: str = typer.Option("human", "--reviewer"),
):
    """确认已持久化的设计工具 draft，不重新生成 request/result。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        with SQLiteExperienceRepository(db) as repository:
            run = repository.get_current("design_tool_run", run_id)
            if run is None:
                raise ValueError(f"DesignToolRun 不存在: {run_id}")
            if run.confirmation != "pending":
                raise ValueError(f"DesignToolRun 不是 pending: {run_id}")
            model_revision_id = run.resulting_model_revision_id
            if not model_revision_id:
                raise ValueError("DesignToolRun 没有关联 resulting model revision")
            model = repository.get_revision("progressive_model", model_revision_id)
            if model is None:
                raise ValueError(f"resulting model revision 不存在: {model_revision_id}")
            updated = ExperienceApplicationService(repository).confirm_design_tool_run(run, model, actor=reviewer)
            rendered = render_progressive_model_markdown(updated) if fmt == "md" else updated.model_dump_json(indent=2)
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(rendered, encoding="utf-8")
                typer.echo(f"已写入 {out}")
            else:
                typer.echo(rendered)
    except (OSError, ValueError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法确认设计工具 draft: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("design-export-request")
def export_design_tool_request(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    candidate_revision: str = typer.Option(..., "--candidate-revision", help="候选 revision ID"),
    out: Path | None = typer.Option(None, "--out", "-o", help="DesignToolRequest JSON 输出文件"),
):
    """导出发送给外部渲染/设计工具的最小结构化请求。"""
    try:
        with SQLiteExperienceRepository(db) as repository:
            candidate = repository.get_revision("candidate", candidate_revision)
            if candidate is None:
                raise ValueError(f"候选 revision 不存在: {candidate_revision}")
            rule_sets = [
                value
                for value in repository.list_revisions("rule_set")
                if value.brief_revision_id == candidate.brief_revision_id
            ]
            if not rule_sets:
                raise ValueError("candidate 没有关联 DesignRuleSet")
            models = [
                value
                for value in repository.list_revisions("progressive_model")
                if value.candidate_revision_id == candidate_revision
            ]
            if not models:
                raise ValueError("candidate 没有关联 ProgressiveDesignModel")
            model = max(models, key=lambda value: value.meta.revision)
            request = build_design_tool_request(candidate, rule_sets[-1], parent_model_revision_id=model.revision_id)
            rendered = request.model_dump_json(indent=2)
    except (OSError, ValueError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法导出设计工具请求: {exc}", err=True)
        raise typer.Exit(code=1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@app.command("design-portfolio")
def export_design_portfolio(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    model_id: str | None = typer.Option(None, "--model-id", help="ProgressiveDesignModel 聚合 ID；省略时使用最新模型"),
    out: Path | None = typer.Option(None, "--out", "-o", help="作品集文件"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    case_id: str = typer.Option("transit-anchor", "--case-id", help="作品集案例 ID"),
    virtual_validation: Path | None = typer.Option(None, "--virtual-validation", help="虚拟工程预检报告 JSON；仅作为非证据设计材料投影"),
    scenario_replay: Path | None = typer.Option(None, "--scenario-replay", help="场景策略演练报告 JSON；仅作为非证据设计材料投影"),
):
    """从 SQLite revision 链生成可持续更新的作品集快照。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    try:
        with SQLiteExperienceRepository(db) as repository:
            all_models = repository.list_revisions("progressive_model")
            if not all_models:
                raise ValueError("数据库中没有 ProgressiveDesignModel")
            if model_id:
                selected_models = [value for value in all_models if value.model_id == model_id]
                if not selected_models:
                    raise ValueError(f"ProgressiveDesignModel 不存在: {model_id}")
            else:
                latest_any = max(all_models, key=lambda value: (value.meta.revision, value.meta.created_at))
                selected_models = [value for value in all_models if value.model_id == latest_any.model_id]
            current_model = max(selected_models, key=lambda value: value.meta.revision)
            all_candidates = repository.list_revisions("candidate")
            candidate_by_revision = {value.candidate_revision_id: value for value in all_candidates}
            lineage: set[str] = set()
            cursor = current_model.candidate_revision_id
            while cursor and cursor not in lineage:
                lineage.add(cursor)
                candidate = candidate_by_revision.get(cursor)
                cursor = candidate.parent_candidate_revision_id if candidate else None
            candidates = [value for value in all_candidates if value.candidate_revision_id in lineage]
            if not candidates:
                raise ValueError("无法从模型 revision 找到候选 lineage")
            brief = repository.get_revision("brief", candidates[0].brief_revision_id)
            if brief is None:
                raise ValueError("候选 lineage 没有关联 DesignBrief")
            models = [value for value in all_models if value.model_id == current_model.model_id and value.candidate_revision_id in lineage]
            runs = [value for value in repository.list_revisions("design_tool_run") if value.candidate_revision_id in lineage or value.resulting_model_revision_id in {item.revision_id for item in models}]
            patch_ids = {patch_id for run in runs for patch_id in run.patch_revision_ids}
            patches = [value for value in repository.list_revisions("patch") if value.revision_id in patch_ids]
            prototype_runs = [value for value in repository.list_revisions("prototype_run") if value.candidate_revision_id in lineage]
            run_ids = {value.run_id for value in prototype_runs}
            observations = [value for value in repository.list_revisions("measurement_observation") if value.run_id in run_ids]
            reviews = [value for value in repository.list_revisions("evidence_review") if value.run_id in run_ids]
            external_assets = [value for value in repository.list_revisions("external_asset") if value.candidate_revision_id in lineage or value.model_revision_id in {item.revision_id for item in models}]
            drafts = [value for value in repository.list_revisions("observation_draft") if value.candidate_revision_id in lineage]
            confirmed_design = repository.list_revisions("confirmed_observation")
            confirmed_design = [value for value in confirmed_design if value.source_fact_id in {fact.fact_id for candidate in candidates for fact in candidate.declared_facts}]
            virtual_report = None
            if virtual_validation is not None:
                virtual_report = VirtualValidationReport.model_validate_json(virtual_validation.read_text(encoding="utf-8"))
                if virtual_report.candidate_revision_id not in lineage:
                    raise ValueError("virtual validation report candidate is outside the selected model lineage")
            replay_report = None
            if scenario_replay is not None:
                replay_report = ScenarioReplayReport.model_validate_json(scenario_replay.read_text(encoding="utf-8"))
            case = build_portfolio_case_study(brief, candidates, models, patches, runs, case_id=case_id, prototype_runs=prototype_runs, observations=observations, evidence_reviews=reviews, external_assets=external_assets, observation_drafts=drafts, confirmed_observations=confirmed_design, virtual_validation=virtual_report, scenario_replay=replay_report)
            rendered = render_portfolio_markdown(case) if fmt == "md" else case.model_dump_json(indent=2)
    except (OSError, ValueError, DomainStateError, RepositoryError) as exc:
        typer.echo(f"错误:无法导出设计作品集: {exc}", err=True)
        raise typer.Exit(code=1)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@app.command("design-iterate")
def iterate_design(
    db: Path = typer.Option(..., "--db", help="experience SQLite 数据库"),
    candidate_revision: str = typer.Option(..., "--candidate-revision", help="父候选 revision ID"),
    patches: Path = typer.Option(..., "--patches", "--patch", help="VariablePatch JSON（单个对象或 patches 数组）"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出新的 progressive model"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    provider: str = typer.Option("none", "--provider", help="none、fake 或 blender；默认只创建参数化 revision"),
    confirm: bool = typer.Option(False, "--confirm", help="人工确认 provider 草案并推进 render/geometry 层"),
    blender_executable: Path | None = typer.Option(None, "--blender-executable", help="Blender 可执行文件路径"),
    blender_output_root: Path = typer.Option("output/experience/blender", "--blender-output-root", help="Blender 派生资产输出目录"),
):
    """将确认后的 VariablePatch 投影为子候选，并可重新生成 blockout。"""
    if fmt not in {"md", "json"}:
        typer.echo("错误:--format 只能是 md 或 json。", err=True)
        raise typer.Exit(code=1)
    if provider not in {"none", "fake", "blender"}:
        typer.echo("错误:--provider 只能是 none、fake 或 blender。", err=True)
        raise typer.Exit(code=1)
    try:
        payload = json.loads(patches.read_text(encoding="utf-8"))
        patch_values = payload.get("patches", payload) if isinstance(payload, dict) else payload
        if isinstance(patch_values, dict):
            patch_values = [patch_values]
        if not isinstance(patch_values, list) or not patch_values:
            raise ValueError("patches JSON 必须是非空数组或包含 patches 数组的对象")
        patch_objects = tuple(VariablePatch.model_validate(value) for value in patch_values)
        with SQLiteExperienceRepository(db) as repository:
            parent = repository.get_revision("candidate", candidate_revision)
            if parent is None:
                raise ValueError(f"父候选 revision 不存在: {candidate_revision}")
            models = [value for value in repository.list_revisions("progressive_model") if value.candidate_revision_id == candidate_revision]
            if not models:
                raise ValueError("父候选没有关联 ProgressiveDesignModel")
            model = max(models, key=lambda value: value.meta.revision)
            rule_sets = [value for value in repository.list_revisions("rule_set") if value.brief_revision_id == parent.brief_revision_id]
            if not rule_sets:
                raise ValueError("candidate 没有关联 DesignRuleSet")
            service = ExperienceApplicationService(repository)
            child, child_model, trace = service.apply_variable_patch_revision(parent, model, patch_objects, actor="system")
            if provider != "none":
                request = build_design_tool_request(
                    child,
                    rule_sets[-1],
                    patches=patch_objects,
                    parent_model_revision_id=model.revision_id,
                )
                if provider == "fake":
                    result = FakeDesignToolProvider().generate(request)
                else:
                    result = BlenderDesignToolProvider(blender_executable, output_root=blender_output_root).generate(request)
                child_model = service.attach_design_tool_result(child_model, result, confirmed=confirm, actor="human" if confirm else "system", request=request)
            if fmt == "json":
                rendered = child_model.model_dump_json(indent=2)
            else:
                rendered = render_progressive_model_markdown(child_model)
                rendered += "\n\n## Parameterized revision\n\n"
                rendered += f"- parent candidate: `{parent.candidate_revision_id}`\n- child candidate: `{child.candidate_revision_id}`\n"
                rendered += f"- applied patches: {', '.join(p.revision_id for p in patch_objects)}\n"
                rendered += f"- repair trace: `{trace.trace_id}`\n"
            if out:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(rendered, encoding="utf-8")
                typer.echo(f"已写入 {out}")
            else:
                typer.echo(rendered)
    except (OSError, ValueError, DomainStateError, json.JSONDecodeError, BlenderProviderError, RepositoryError) as exc:
        typer.echo(f"错误:无法创建参数化设计 revision: {exc}", err=True)
        raise typer.Exit(code=1)


def _growth_store(store: Path) -> GrowthStore:
    return GrowthStore(store.parent)


def _strategy_store(store: Path) -> StrategyStore:
    return StrategyStore(store.parent)


@app.command()
def analyze(
    input: Path = typer.Option(..., "--input", "-i", help="产品描述文本文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出文件;省略则打印"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    use_memory: bool = typer.Option(False, "--use-memory", help="检索相似历史案例并注入分析"),
    no_save: bool = typer.Option(False, "--no-save", help="不把本次结果落盘案例库"),
    use_strategies: bool = typer.Option(False, "--use-strategies", help="注入已批准的拆解策略卡"),
    self_review: bool = typer.Option(False, "--self-review",
                                     help="拆解后追加一次 LLM 自评(默认关)"),
    max_n: int = typer.Option(8, "--max-n", help="送入映射的框架数上限;等于库容量即不截断"),
    min_n: int = typer.Option(5, "--min-n", help="框架数下限;不足时按库序补齐"),
    provider: str = typer.Option("claude", "--provider", hidden=True,
                                 envvar="PSYTEARDOWN_LLM"),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True,
                                       envvar="PSYTEARDOWN_EMBED"),
):
    """拆解一个产品描述,输出结构化报告;默认落盘为案例。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)

    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    outcome = analyze_product(
        llm, text, store=store, now=now,
        embed_factory=lambda: _build_embed_provider(embed_provider),
        use_memory=use_memory, no_save=no_save,
        use_strategies=use_strategies, self_review=self_review, fmt=fmt,
        max_n=max_n, min_n=min_n, review_fn=review_case,
    )
    for w in outcome.warnings:
        typer.echo(w, err=True)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(outcome.rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(outcome.rendered)
        typer.echo(f"\n证据溯源记账: kept={outcome.result.grounding.kept}, dropped={outcome.result.grounding.dropped}")
    if outcome.case_id:
        typer.echo(f"已落盘案例 {outcome.case_id}")


@app.command()
def review(
    case_id: str = typer.Argument(..., help="案例 id(见 analyze 落盘输出)"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    to_reflect: bool = typer.Option(False, "--to-reflect",
                                    help="把自评改进建议蒸馏成候选策略卡(待人工审批)"),
    provider: str = typer.Option("claude", "--provider", hidden=True,
                                 envvar="PSYTEARDOWN_LLM"),
):
    """对历史案例补做批判自评(覆盖旧自评);可选直达策略蒸馏管道。"""
    case_store = CaseStore(store)
    hit = case_store.get_with_embedding(case_id)
    if hit is None:
        typer.echo(f"案例不存在:{case_id}", err=True)
        raise typer.Exit(code=1)
    case, emb = hit

    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 用户显式要求自评:失败直接报错,不静默(与 analyze 内降级不同)。
    rev = review_case(llm, case.result, reviewed_at=now,
                      model_label=case.result.meta.model)
    case.review = rev
    case_store.save(case, emb)

    typer.echo(f"自评完成:{case_id} 总体评分 {rev.score:.2f}")
    for w in rev.weaknesses:
        typer.echo(f"- 缺陷:{w}")
    for s in rev.suggestions:
        typer.echo(f"- 建议:{s}")

    if to_reflect:
        if not rev.suggestions:
            typer.echo("无改进建议,跳过策略蒸馏。")
            return
        note = (f"对案例「{case.product_name}」拆解的自评改进建议:\n"
                + "\n".join(f"- {s}" for s in rev.suggestions))
        cards = distill_from_note(llm, note, created_at=now)
        sstore = _strategy_store(store)
        for card in cards:
            sstore.save_candidate(card)
        typer.echo(f"蒸馏出 {len(cards)} 张候选策略卡(待审):"
                   + ", ".join(c.id for c in cards))


@app.command()
def similar(
    input: Path = typer.Option(..., "--input", "-i", help="产品描述文本文件"),
    top_k: int = typer.Option(3, "--top-k", help="返回最相似的前 K 个案例"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True,
                                       envvar="PSYTEARDOWN_EMBED"),
):
    """检索与给定描述最相似的历史案例。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)
    emb = _build_embed_provider(embed_provider)
    case_store = CaseStore(store)
    hits = search_similar(case_store, emb, text, top_k=top_k)
    if not hits:
        typer.echo("案例库为空或无相似案例。")
        return
    for case, score in hits:
        fw = ", ".join(case.frameworks_used) or "—"
        typer.echo(f"{score:.3f}  {case.product_name} — {case.one_liner}  ({fw})")


@memory_app.command("stats")
def memory_stats(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """显示案例库统计。"""
    case_store = CaseStore(store)
    typer.echo(f"案例数:{case_store.count()}")


@kb_app.command("list")
def kb_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径(用于合并习得框架)"),
):
    """列出已加载的框架(含已批准的习得框架)。"""
    for fw in load_frameworks(learned_dir=_growth_store(store).learned_dir()):
        typer.echo(f"{fw.id}\t{fw.name}\t({fw.category})")


@kb_app.command("show")
def kb_show(
    framework_id: str = typer.Argument(..., help="框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径(用于合并习得框架)"),
):
    """查看某框架详情(含已批准的习得框架)。"""
    for fw in load_frameworks(learned_dir=_growth_store(store).learned_dir()):
        if fw.id == framework_id:
            typer.echo(f"# {fw.name} ({fw.id})\n{fw.summary}\n")
            for p in fw.principles:
                typer.echo(f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})")
            return
    typer.echo(f"未找到框架:{framework_id}", err=True)
    raise typer.Exit(code=1)


@app.command()
def learn(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    min_support: int = typer.Option(3, "--min-support", help="候选需的最少支撑案例数"),
    provider: str = typer.Option("claude", "--provider", hidden=True,
                                 envvar="PSYTEARDOWN_LLM"),
    embed_provider: str = typer.Option("local", "--embed-provider", hidden=True,
                                       envvar="PSYTEARDOWN_EMBED"),
):
    """从案例库提炼现有框架盖不住的候选新框架(待人工审批)。"""
    cases = [c for c, _ in CaseStore(store).all()]
    if not cases:
        typer.echo("案例库为空,先用 analyze 积累案例再 learn。")
        return
    gstore = _growth_store(store)
    existing = load_frameworks(learned_dir=gstore.learned_dir())
    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cands = propose_frameworks(llm, cases, existing, created_at=now,
                               min_support=min_support)

    # 去重(嵌入是增强;不可用则降级为 id/name 去重)
    emb: EmbeddingProvider | None = None
    try:
        emb = _build_embed_provider(embed_provider)
        emb.embed(["预热"])  # 触发懒加载,离线会在此失败
    except Exception as e:  # noqa: BLE001
        typer.echo(f"提示:嵌入不可用({e}),去重降级为 id/name。", err=True)
        emb = None
    cands = filter_duplicates(cands, existing, embed=emb)

    for cand in cands:
        gstore.save_candidate(cand)
    typer.echo(f"提炼出 {len(cands)} 个候选框架(待审):"
               + ", ".join(c.framework.id for c in cands))


@candidates_app.command("list")
def candidates_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """列出待审候选框架。"""
    cands = _growth_store(store).list_candidates()
    if not cands:
        typer.echo("无候选。")
        return
    for c in cands:
        typer.echo(f"{c.framework.id}\t{c.framework.name}\t(支撑 {len(c.source_case_ids)} 例)")


@candidates_app.command("show")
def candidates_show(
    framework_id: str = typer.Argument(..., help="候选框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """查看候选详情。"""
    from psyteardown.growth.store import GrowthError

    try:
        c = _growth_store(store).get_candidate(framework_id)
    except GrowthError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    if c is None:
        typer.echo(f"候选不存在:{framework_id}", err=True)
        raise typer.Exit(code=1)
    fw = c.framework
    typer.echo(f"# {fw.name} ({fw.id}) — {fw.category}\n{fw.summary}\n")
    typer.echo(f"提案理由:{c.rationale}")
    typer.echo(f"支撑案例:{', '.join(c.source_case_ids)}\n")
    for p in fw.principles:
        typer.echo(f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})")


@candidates_app.command("approve")
def candidates_approve(
    framework_id: str = typer.Argument(..., help="候选框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """批准候选,写入习得层(此后 analyze 生效)。"""
    from psyteardown.growth.store import GrowthError

    try:
        path = _growth_store(store).approve(framework_id)
    except GrowthError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已批准 {framework_id} → {path}")


@candidates_app.command("reject")
def candidates_reject(
    framework_id: str = typer.Argument(..., help="候选框架 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """驳回并删除候选。"""
    from psyteardown.growth.store import GrowthError

    try:
        _growth_store(store).reject(framework_id)
    except GrowthError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已驳回 {framework_id}")


@app.command()
def strategize(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    min_support: int = typer.Option(3, "--min-support", help="策略卡需的最少支撑案例数"),
    provider: str = typer.Option("claude", "--provider", hidden=True,
                                 envvar="PSYTEARDOWN_LLM"),
):
    """从案例库跨案例归纳候选策略卡(待人工审批)。"""
    cases = [c for c, _ in CaseStore(store).all()]
    if not cases:
        typer.echo("案例库为空,先用 analyze 积累案例再 strategize。")
        return
    sstore = _strategy_store(store)
    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards = propose_strategies(llm, cases, created_at=now, min_support=min_support)
    for card in cards:
        sstore.save_candidate(card)
    typer.echo(f"提炼出 {len(cards)} 张候选策略卡(待审):"
               + ", ".join(c.id for c in cards))


@app.command()
def reflect(
    note: str = typer.Option(..., "--note", help="你的拆解复盘笔记"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
    provider: str = typer.Option("claude", "--provider", hidden=True,
                                 envvar="PSYTEARDOWN_LLM"),
):
    """把自然语言复盘蒸馏成候选策略卡(待人工审批)。"""
    sstore = _strategy_store(store)
    llm = _build_provider(provider)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards = distill_from_note(llm, note, created_at=now)
    for card in cards:
        sstore.save_candidate(card)
    typer.echo(f"蒸馏出 {len(cards)} 张候选策略卡(待审):"
               + ", ".join(c.id for c in cards))


@strategies_app.command("list")
def strategies_list(
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """列出待审策略卡。"""
    cards = _strategy_store(store).list_candidates()
    if not cards:
        typer.echo("无候选策略卡。")
        return
    for c in cards:
        typer.echo(f"{c.id}\t[{c.target_step}]\t{c.rule}")


@strategies_app.command("show")
def strategies_show(
    strategy_id: str = typer.Argument(..., help="策略卡 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """查看策略卡详情。"""
    from psyteardown.strategy.store import StrategyError

    try:
        c = _strategy_store(store).get_candidate(strategy_id)
    except StrategyError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    if c is None:
        typer.echo(f"候选不存在:{strategy_id}", err=True)
        raise typer.Exit(code=1)
    applies = ", ".join(c.applies_to) or "(通用)"
    typer.echo(f"# {c.id} [{c.target_step}] 适用:{applies}\n规则:{c.rule}\n")
    typer.echo(f"依据:{c.rationale}")
    typer.echo(f"支撑案例:{', '.join(c.source_case_ids) or '(人工复盘)'}")


@strategies_app.command("approve")
def strategies_approve(
    strategy_id: str = typer.Argument(..., help="策略卡 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """批准策略卡(此后 analyze --use-strategies 生效)。"""
    from psyteardown.strategy.store import StrategyError

    try:
        path = _strategy_store(store).approve(strategy_id)
    except StrategyError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已批准 {strategy_id} → {path}")


@strategies_app.command("reject")
def strategies_reject(
    strategy_id: str = typer.Argument(..., help="策略卡 id"),
    store: Path = typer.Option(DEFAULT_STORE, "--store", help="案例库路径"),
):
    """驳回并删除策略卡。"""
    from psyteardown.strategy.store import StrategyError

    try:
        _strategy_store(store).reject(strategy_id)
    except StrategyError as e:
        typer.echo(f"错误:{e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"已驳回 {strategy_id}")


if __name__ == "__main__":
    app()
