from pathlib import Path

import pytest

from psyteardown.experience import (
    DomainStateError,
    EngineeringArtifactRef,
    EngineeringOrchestrator,
    EngineeringRequirement,
    EngineeringToolCoordinator,
    EngineeringToolRequest,
    RawEngineeringToolResult,
    RevisionMeta,
    SQLiteExperienceRepository,
    dependency_ref,
)


def _requirement(revision: int = 1) -> EngineeringRequirement:
    return EngineeringRequirement(
        requirement_id="thermal-limit",
        revision_id=f"thermal-limit.r{revision}",
        meta=RevisionMeta(
            revision=revision,
            parent_revision_id=f"thermal-limit.r{revision - 1}" if revision > 1 else None,
            created_by="system-engineer",
            reason="thermal requirement",
        ),
        title="bounded surface temperature",
        acceptance_criteria=("surface temperature remains below declared threshold",),
    )


def _request() -> EngineeringToolRequest:
    return EngineeringToolRequest(
        request_id="thermal-request",
        revision_id="thermal-request.r1",
        meta=RevisionMeta(revision=1, created_by="ai-orchestrator", reason="thermal CAE request"),
        tool_domain="cae",
        operation="steady-state thermal analysis",
        tool="real-solver",
        tool_version="2026.1",
        output_object_id="thermal-run",
        parameters={"ambient_c": 25, "power_w": 1.2},
        requested_outputs=("temperature field", "solver log"),
        dependencies=(dependency_ref("engineering_requirement", "thermal-limit", 1),),
    )


def _result() -> RawEngineeringToolResult:
    return RawEngineeringToolResult(
        result_id="thermal-result",
        revision_id="thermal-result.r1",
        meta=RevisionMeta(revision=1, created_by="solver-adapter", reason="raw solver output"),
        request_revision_id="thermal-request.r1",
        tool_domain="cae",
        provider="lab-workstation",
        tool="real-solver",
        tool_version="2026.1",
        execution_status="succeeded",
        convergence_status="converged",
        artifacts=(EngineeringArtifactRef(
            artifact_id="thermal-field",
            uri="results/thermal-field.vtk",
            sha256="a" * 64,
            role="solver_output",
        ),),
        raw_metadata={"exit_code": 0},
    )


def test_raw_result_interpretation_and_human_projection_are_separate(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "tools.db") as repo:
        registry = EngineeringOrchestrator(repo)
        registry.register("requirement", _requirement())
        coordinator = EngineeringToolCoordinator(repo)
        request = coordinator.prepare_request(_request())
        raw = coordinator.import_raw_result(_result())
        assert raw.physical_evidence is False
        interpretation = coordinator.create_interpretation(
            raw,
            interpretation_id="thermal-interpretation",
            summary="solver field remains within the declared simulated boundary",
            findings=("peak node occurs near the processor",),
            limitations=("simulation does not replace a thermocouple measurement",),
            structured_payload={"uncertainty": ["contact resistance not measured"]},
        )
        with pytest.raises(DomainStateError, match="accepted human review"):
            coordinator.project_reviewed_result(interpretation)
        with pytest.raises(DomainStateError, match="human reviewer"):
            coordinator.review_interpretation(
                interpretation,
                reviewer="ai-agent",
                decision="accepted",
                rationale="automatic approval is forbidden",
            )
        reviewed = coordinator.review_interpretation(
            interpretation,
            reviewer="thermal-engineer-li",
            decision="accepted",
            rationale="inputs, convergence and limitations reviewed",
        )
        projected = coordinator.project_reviewed_result(reviewed)
        assert projected.analysis_type == "steady-state thermal analysis"
        assert projected.convergence_status == "converged"
        assert projected.raw_result_uri == "results/thermal-field.vtk"
        assert projected.reviewer == "thermal-engineer-li"
        assert repo.get_revision("raw_engineering_tool_result", raw.revision_id).raw_metadata == {"exit_code": 0}
        assert repo.get_revision("engineering_interpretation", reviewed.revision_id).summary == reviewed.summary


def test_changed_input_invalidates_request_result_interpretation_and_projection(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "stale-tools.db") as repo:
        registry = EngineeringOrchestrator(repo)
        registry.register("requirement", _requirement())
        coordinator = EngineeringToolCoordinator(repo)
        coordinator.prepare_request(_request())
        raw = coordinator.import_raw_result(_result())
        interpretation = coordinator.create_interpretation(
            raw,
            interpretation_id="thermal-interpretation",
            summary="draft interpretation",
        )
        reviewed = coordinator.review_interpretation(
            interpretation,
            reviewer="thermal-engineer-li",
            decision="accepted",
            rationale="reviewed",
        )
        coordinator.project_reviewed_result(reviewed)

        registry.register("requirement", _requirement(2))
        stale_types = {type(item).__name__ for item in registry.stale_objects()}
        assert {
            "EngineeringToolRequest",
            "RawEngineeringToolResult",
            "EngineeringInterpretation",
            "CAEAnalysisRun",
        }.issubset(stale_types)


def test_result_is_rejected_when_pinned_input_revision_changed(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "stale-request.db") as repo:
        registry = EngineeringOrchestrator(repo)
        registry.register("requirement", _requirement())
        coordinator = EngineeringToolCoordinator(repo)
        coordinator.prepare_request(_request())
        registry.register("requirement", _requirement(2))
        with pytest.raises(DomainStateError, match="stale"):
            coordinator.import_raw_result(_result())
