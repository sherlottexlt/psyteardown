import json

from typer.testing import CliRunner

from psyteardown.cli import app
from psyteardown.pipeline.schemas import (
    ExperienceAssessment,
    GroundingStats,
    ProductProfile,
    TeardownMeta,
    TeardownResult,
)


runner = CliRunner()


def test_engineering_cli_initializes_reviews_and_reports_status(tmp_path):
    source = tmp_path / "intake.json"
    database = tmp_path / "engineering.db"
    source.write_text(json.dumps({
        "intake_id": "cli-intake",
        "project_id": "cli-project",
        "revision_id": "cli-intake.r1",
        "meta": {
            "revision": 1,
            "created_by": "product-owner",
            "reason": "declared intake",
        },
        "scenario": "public transit while walking",
        "product_purpose": "provide a bounded wearable cancellation control",
        "target_segment": "consented adult commuters",
        "declared_requirements": [{
            "requirement_id": "cli-cancel",
            "title": "explicit cancellation",
            "description": "provide a cancel action",
            "requirement_type": "must",
            "acceptance_criteria": ["physical task test verifies cancellation"],
            "source": "product-owner interview",
        }],
    }, ensure_ascii=False), encoding="utf-8")

    initialized = runner.invoke(app, [
        "engineering-init", "--db", str(database), "--input", str(source),
    ])
    assert initialized.exit_code == 0, initialized.stdout
    payload = json.loads(initialized.stdout)
    assert payload["project"]["stage"] == "concept_declared"
    assert any(item["source_type"] == "ai_default" for item in payload["requirements"])

    reviewed = runner.invoke(app, [
        "engineering-requirements-review",
        "--db", str(database),
        "--project-id", "cli-project",
        "--reviewer", "system-engineer-li",
        "--rationale", "sources and acceptance criteria reviewed",
    ])
    assert reviewed.exit_code == 0, reviewed.stdout
    review_payload = json.loads(reviewed.stdout)
    assert {item["role"] for item in review_payload["ready_tasks"]} == {
        "industrial_design", "structural_engineering", "material_process"
    }

    status = runner.invoke(app, [
        "engineering-status", "--db", str(database), "--project-id", "cli-project",
    ])
    assert status.exit_code == 0, status.stdout
    status_payload = json.loads(status.stdout)
    assert status_payload["project"]["stage"] == "concept_declared"
    assert all(item["status"] == "approved" for item in status_payload["requirements"])

    traceability = runner.invoke(app, [
        "engineering-traceability",
        "--db", str(database),
        "--project-id", "cli-project",
        "--format", "json",
    ])
    assert traceability.exit_code == 0, traceability.stdout
    trace_payload = json.loads(traceability.stdout)
    assert trace_payload["status"] == "blocked"
    assert "must_requirement_has_no_reviewed_passing_test" in {
        issue["code"] for issue in trace_payload["issues"]
    }


def test_engineering_cli_can_initialize_from_teardown_json(tmp_path):
    source = tmp_path / "teardown.json"
    database = tmp_path / "engineering.db"
    source.write_text(TeardownResult(
        product=ProductProfile(
            name="Transit Anchor",
            product_type="wearable",
            one_liner="provide bounded cancellation control",
            touchpoints=["shared transit"],
        ),
        grounding=GroundingStats(kept=1),
        assessment=ExperienceAssessment(
            friction_points=["hard to cancel while walking"],
            ethics_warnings=["private content may be exposed"],
            opportunities=["make cancellation explicit"],
        ),
        executive_summary="summary",
        meta=TeardownMeta(model="fake", generated_at="2026-09-17"),
    ).model_dump_json(), encoding="utf-8")
    result = runner.invoke(app, [
        "engineering-init-from-teardown",
        "--db", str(database),
        "--input", str(source),
        "--project-id", "teardown-project",
        "--scenario", "walking in shared transit",
        "--target-segment", "consented commuters",
    ])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["intake"]["discovery_quality"] == "grounded"
    assert payload["review_required"] is True
    assert any("discovery" in item["requirement_id"] for item in payload["requirements"])


def test_discovery_cli_requires_triage_and_projects_only_device_candidates(tmp_path):
    source = tmp_path / "teardown.json"
    database = tmp_path / "experience.db"
    source.write_text(TeardownResult(
        product=ProductProfile(
            name="Transit Anchor",
            product_type="wearable companion App",
            one_liner="coordinate bounded cancellation across App and device",
            touchpoints=["shared transit"],
        ),
        grounding=GroundingStats(kept=1),
        assessment=ExperienceAssessment(
            friction_points=["hard to cancel while walking"],
            ethics_warnings=["private content may be exposed"],
            opportunities=["make cancellation explicit"],
        ),
        executive_summary="summary",
        meta=TeardownMeta(model="fake", generated_at="2026-09-17"),
    ).model_dump_json(), encoding="utf-8")

    imported = runner.invoke(app, [
        "discovery", "import-teardown",
        "--db", str(database), "--input", str(source),
        "--discovery-id", "cli-discovery",
    ])
    assert imported.exit_code == 0, imported.stdout
    discovery = json.loads(imported.stdout)
    assert discovery["triage_status"] == "pending"
    signals = discovery["signals"]
    decisions = [
        {
            "signal_id": signals[0]["signal_id"],
            "disposition": "device_interaction_candidate",
            "rationale": "affects no-phone operation",
            "candidate_statement": "device exposes an explicit cancellation path",
            "validation_question": "can the user cancel while walking without opening the App?",
        },
        {
            "signal_id": signals[1]["signal_id"],
            "disposition": "cross_channel_validation",
            "rationale": "privacy spans App and device",
            "validation_question": "does device output expose private content in public?",
        },
        {
            "signal_id": signals[2]["signal_id"],
            "disposition": "app_experience",
            "rationale": "remains an App opportunity",
        },
    ]
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
    triaged = runner.invoke(app, [
        "discovery", "triage",
        "--db", str(database), "--discovery-id", "cli-discovery",
        "--decisions", str(decisions_path), "--reviewer", "experience-lead-li",
        "--rationale", "triaged App and device boundaries",
    ])
    assert triaged.exit_code == 0, triaged.stdout
    assert json.loads(triaged.stdout)["triage_status"] == "complete"

    projected = runner.invoke(app, [
        "discovery", "project-to-engineering",
        "--db", str(database), "--discovery-id", "cli-discovery",
        "--project-id", "cli-cross-device",
        "--scenario", "walking in shared transit",
        "--target-segment", "consented commuters",
    ])
    assert projected.exit_code == 0, projected.stdout
    payload = json.loads(projected.stdout)
    candidates = [
        item for item in payload["requirements"]
        if "device-interaction" in item["requirement_id"]
    ]
    assert len(candidates) == 1
    assert candidates[0]["requirement_type"] == "explore"
    assert candidates[0]["status"] == "draft"
    assert candidates[0]["hard_constraint"] is False
