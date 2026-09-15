import json
from pathlib import Path

from typer.testing import CliRunner

from psyteardown.cli import app


runner = CliRunner()


def request_payload() -> dict:
    return {
        "brief_id": "brief-cli",
        "product_category": "未来可穿戴 AI 伴行助手",
        "goal": "在移动中提供低打扰、可撤销的介入",
        "target_segment": "需要在移动中保持任务连续性的知识工作者",
        "context": "城市通勤和任务切换中的连续使用",
        "criteria": [
            {
                "criterion_id": "control",
                "name": "控制感",
                "operational_definition": "用户可以接受、拒绝、延后或纠正一次介入",
            }
        ],
        "required_capabilities": ["local policy gate", "bounded recovery"],
    }


def test_design_command_writes_complete_markdown_batch(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "design.md"

    result = runner.invoke(app, ["design", "--input", str(source), "--out", str(output)])

    assert result.exit_code == 0, result.stdout
    markdown = output.read_text(encoding="utf-8")
    assert markdown.count("## Variant ") == 5
    assert "功能架构" in markdown
    assert "安全与失败模式" in markdown
    assert "明确未知与待验证" in markdown


def test_design_command_can_render_one_explicit_variant_as_json(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "variant.json"

    result = runner.invoke(
        app,
        ["design", "--input", str(source), "--format", "json", "--variant", "2", "--out", str(output)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["candidate_id"] == "scaffold-r1-3"
    assert payload["design"]["components"]
    assert payload["design"]["verification_plan"]


def test_design_command_persists_experience_run_to_sqlite(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "design.md"
    database = tmp_path / "experience.db"

    result = runner.invoke(
        app,
        ["design", "--input", str(source), "--out", str(output), "--db", str(database)],
    )

    assert result.exit_code == 0, result.stdout
    from psyteardown.experience.sqlite import SQLiteExperienceRepository

    with SQLiteExperienceRepository(database) as repository:
        assert repository.get_current("brief", "brief-cli") is not None
        assert repository.get_current("iteration", repository.list_revisions("iteration")[0].iteration_id) is not None
        assert len(repository.list_revisions("candidate")) == 5
        assert any(event.event_type == "BriefFrozen" for event in repository.domain_events)


def test_design_command_rejects_invalid_request_and_format(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["design", "--input", str(source), "--format", "yaml"])

    assert result.exit_code != 0
    assert "md 或 json" in result.output


def test_design_attach_records_draft_then_confirmed_model_revision(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "experience.db"
    generated = runner.invoke(app, ["design", "--input", str(source), "--db", str(database), "--out", str(tmp_path / "batch.md")])
    assert generated.exit_code == 0, generated.stdout

    from psyteardown.experience.sqlite import SQLiteExperienceRepository

    with SQLiteExperienceRepository(database) as repository:
        candidate_revision = repository.list_revisions("candidate")[0].candidate_revision_id
    draft_output = tmp_path / "draft.md"
    result = runner.invoke(app, ["design-attach", f"--db={database}", f"--candidate-revision={candidate_revision}", f"--out={draft_output}"])
    assert result.exit_code == 0, result.stdout
    assert "structured_design" in draft_output.read_text(encoding="utf-8")
    assert "missing" in draft_output.read_text(encoding="utf-8")

    confirmed_output = tmp_path / "confirmed.md"
    result = runner.invoke(app, ["design-attach", f"--db={database}", f"--candidate-revision={candidate_revision}", f"--out={confirmed_output}", "--confirm"])
    assert result.exit_code == 0, result.stdout
    confirmed = confirmed_output.read_text(encoding="utf-8")
    assert "geometry_ready" in confirmed
    assert "complete" in confirmed
    with SQLiteExperienceRepository(database) as repository:
        models = repository.list_revisions("progressive_model")
        assert len(models) == 7  # 5 baselines + draft and confirmed revisions
        assert models[-1].stage == "geometry_ready"
        runs = repository.list_revisions("design_tool_run")
        assert len(runs) == 2
        assert {run.confirmation for run in runs} == {"pending", "confirmed"}
        assert all(run.parent_model_revision_id for run in runs)


def test_design_review_confirms_existing_pending_run_without_new_request(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "experience.db"
    assert runner.invoke(
        app,
        ["design", "--input", str(source), "--db", str(database), "--out", str(tmp_path / "batch.md")],
    ).exit_code == 0
    from psyteardown.experience.sqlite import SQLiteExperienceRepository

    with SQLiteExperienceRepository(database) as repository:
        candidate_revision = repository.list_revisions("candidate")[0].candidate_revision_id
    draft = runner.invoke(app, ["design-attach", "--db", str(database), "--candidate-revision", candidate_revision])
    assert draft.exit_code == 0, draft.output
    with SQLiteExperienceRepository(database) as repository:
        pending = repository.list_revisions("design_tool_run")[-1]
        pending_request_id = pending.request_json["request_id"]
        pending_model_revision = pending.resulting_model_revision_id
        run_id = pending.run_id

    confirmed = runner.invoke(app, ["design-review", "--db", str(database), "--run-id", run_id, "--format", "json"])
    assert confirmed.exit_code == 0, confirmed.output
    payload = json.loads(confirmed.output)
    assert payload["stage"] == "geometry_ready"
    with SQLiteExperienceRepository(database) as repository:
        runs = repository.list_revisions("design_tool_run", run_id)
        assert len(runs) == 2
        assert runs[-1].confirmation == "confirmed"
        assert runs[-1].request_json["request_id"] == pending_request_id
        assert runs[-1].resulting_model_revision_id != pending_model_revision


def test_design_tool_request_can_be_exported_and_external_result_attached(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "experience.db"
    assert runner.invoke(app, ["design", "--input", str(source), "--db", str(database), "--out", str(tmp_path / "batch.md")]).exit_code == 0
    from psyteardown.experience.sqlite import SQLiteExperienceRepository
    with SQLiteExperienceRepository(database) as repository:
        candidate_revision = repository.list_revisions("candidate")[0].candidate_revision_id

    request_file = tmp_path / "tool-request.json"
    exported = runner.invoke(app, ["design-export-request", f"--db={database}", f"--candidate-revision={candidate_revision}", f"--out={request_file}"])
    assert exported.exit_code == 0, exported.stdout
    tool_request = json.loads(request_file.read_text(encoding="utf-8"))
    assert tool_request["candidate_revision_id"] == candidate_revision
    assert tool_request["parent_model_revision_id"]
    assert "Preserve explicit unknowns" in tool_request["prompt_projection"]

    result_file = tmp_path / "tool-result.json"
    result_file.write_text(json.dumps({
        "request_id": tool_request["request_id"],
        "candidate_revision_id": candidate_revision,
        "provider": "external-mock",
        "model": "render-v1",
        "render_asset_refs": ["asset://render/mock-1"],
        "geometry_asset_refs": [],
        "unknowns": ["geometry dimensions"],
    }), encoding="utf-8")
    output = tmp_path / "attached.json"
    attached = runner.invoke(app, ["design-attach", f"--db={database}", f"--candidate-revision={candidate_revision}", f"--result={result_file}", "--confirm", "--format=json", f"--out={output}"])
    assert attached.exit_code == 0, attached.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["stage"] == "render_ready"
    assert payload["provider_result_ids"]
    with SQLiteExperienceRepository(database) as repository:
        runs = repository.list_revisions("design_tool_run")
        assert runs[-1].confirmation == "confirmed"
        assert runs[-1].result_json["result_id"] == payload["provider_result_ids"][-1]


def test_prototype_import_rejects_unfilled_handoff_templates(tmp_path):
    database = tmp_path / "experience.db"

    result = runner.invoke(
        app,
        [
            "prototype-import",
            "--db",
            str(database),
            "--run",
            "examples/transit-anchor-round2-prototype-run-template.json",
            "--observations",
            "examples/transit-anchor-round2-measurement-observations-template.json",
        ],
    )

    assert result.exit_code != 0
    assert "template placeholder" in result.output
    from psyteardown.experience.sqlite import SQLiteExperienceRepository

    with SQLiteExperienceRepository(database) as repository:
        assert repository.list_revisions("prototype_run") == []
        assert repository.list_revisions("measurement_observation") == []


def test_prototype_import_snapshots_known_transit_protocol(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "experience.db"
    assert runner.invoke(
        app,
        ["design", "--input", str(source), "--db", str(database), "--out", str(tmp_path / "batch.md")],
    ).exit_code == 0

    from psyteardown.experience.sqlite import SQLiteExperienceRepository

    with SQLiteExperienceRepository(database) as repository:
        candidate = repository.list_revisions("candidate")[0]
        model = repository.list_revisions("progressive_model")[0]

    run = {
        "run_id": "round2-run-20260914-01",
        "revision_id": "round2-run-20260914-01.r1",
        "meta": {"revision": 1, "created_by": "human", "reason": "physical prototype import"},
        "protocol_id": "transit-anchor-physical-validation/v1",
        "protocol_revision": "v1",
        "candidate_revision_id": candidate.candidate_revision_id,
        "model_revision_id": model.revision_id,
        "device_revision": "prototype-build-r1",
        "conditions": ["one hand free"],
        "participant_scope": "consented adults; de-identified scope A",
        "context_scope": "controlled lab proxy",
        "status": "imported",
        "import_source": "manual",
    }
    run_file = tmp_path / "run.json"
    run_file.write_text(json.dumps(run), encoding="utf-8")
    observations_file = tmp_path / "observations.json"
    observations_file.write_text(
        json.dumps(
            {
                "observations": [
                    {
                        "observation_id": "round2-obs-stop-path-20260914-01",
                        "revision_id": "round2-obs-stop-path-20260914-01.r1",
                        "meta": {"revision": 1, "created_by": "human", "reason": "raw measurement import"},
                        "run_id": run["run_id"],
                        "measure_id": "stop-path",
                        "metric": "completion time",
                        "method": "manual stopwatch",
                        "condition": "one hand free",
                        "value": 840,
                        "unit": "ms",
                        "participant_scope": run["participant_scope"],
                        "context_scope": run["context_scope"],
                        "status": "draft",
                        "provenance": "prototype_measurement",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["prototype-import", "--db", str(database), "--run", str(run_file), "--observations", str(observations_file)],
    )
    assert result.exit_code == 0, result.output

    with SQLiteExperienceRepository(database) as repository:
        imported_run = repository.get_current("prototype_run", run["run_id"])
        assert imported_run is not None
        measure_ids = {item["measure_id"] for item in imported_run.protocol_snapshot["measures"]}
        assert "stop-path" in measure_ids
        imported = repository.get_current("measurement_observation", "round2-obs-stop-path-20260914-01")
        assert imported is not None
        assert imported.status == "draft"
        assert repository.list_revisions("evidence_review") == []


def test_portfolio_can_project_virtual_validation_without_promoting_evidence(tmp_path):
    source = tmp_path / "request.json"
    source.write_text(json.dumps(request_payload(), ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "experience.db"
    assert runner.invoke(
        app,
        ["design", "--input", str(source), "--db", str(database), "--out", str(tmp_path / "batch.md")],
    ).exit_code == 0

    from psyteardown.experience.sqlite import SQLiteExperienceRepository

    with SQLiteExperienceRepository(database) as repository:
        model = repository.list_revisions("progressive_model")[0]
        candidate_revision = model.candidate_revision_id

    virtual_input = json.loads(Path("examples/transit-anchor-round2-virtual-validation-input.json").read_text(encoding="utf-8"))
    virtual_input["candidate_revision_id"] = candidate_revision
    virtual_input["model_revision_id"] = model.revision_id
    virtual_source = tmp_path / "virtual-input.json"
    virtual_source.write_text(json.dumps(virtual_input), encoding="utf-8")
    virtual_report = tmp_path / "virtual-report.json"
    assert runner.invoke(
        app,
        ["virtual-validate", "--input", str(virtual_source), "--format", "json", "--out", str(virtual_report)],
    ).exit_code == 0

    portfolio = tmp_path / "portfolio.md"
    result = runner.invoke(
        app,
        [
            "design-portfolio",
            "--db",
            str(database),
            "--model-id",
            model.model_id,
            "--virtual-validation",
            str(virtual_report),
            "--out",
            str(portfolio),
        ],
    )
    assert result.exit_code == 0, result.output
    rendered = portfolio.read_text(encoding="utf-8")
    assert "Virtual engineering preflight" in rendered
    assert "Evidence level:** `none`" in rendered
    assert "Prototype runs:** 0" in rendered
