"""P3 CAD/CAE/DFM/BOM adapter and human-review coordination boundary."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, Protocol

from psyteardown.experience.engineering import (
    BOMRevision,
    CADArtifact,
    CAEAnalysisRun,
    DFMReview,
    EngineeringArtifactRef,
    EngineeringInterpretation,
    EngineeringOrchestrator,
    EngineeringToolRequest,
    RawEngineeringToolResult,
    canonical_object_type,
)
from psyteardown.experience.models import DependencyRef, DomainStateError, RevisionMeta
from psyteardown.experience.multimodal import is_named_human_actor


class EngineeringToolAdapter(Protocol):
    """Adapter contract for a real external engineering tool."""

    def execute(self, request: EngineeringToolRequest) -> RawEngineeringToolResult: ...


_PROJECTION_TYPES = {
    "cad": "cad_artifact",
    "cae": "cae_analysis_run",
    "dfm": "dfm_review",
    "bom": "bom_revision",
}


class EngineeringToolCoordinator:
    """Pins inputs, stores raw outputs, and enforces human review."""

    def __init__(self, repository: Any, *, actor: str = "ai-engineering-orchestrator") -> None:
        self.repository = repository
        self.registry = EngineeringOrchestrator(repository, actor=actor)
        self.actor = actor

    def _require_current_dependencies(self, dependencies: Iterable[DependencyRef]) -> None:
        for dependency in dependencies:
            object_type = canonical_object_type(dependency.object_type)
            current = self.repository.get_current(object_type, dependency.object_id)
            if current is None:
                raise DomainStateError(
                    f"engineering tool dependency is unavailable: {object_type}:{dependency.object_id}"
                )
            if current.meta.revision != dependency.revision:
                raise DomainStateError(
                    f"engineering tool dependency is stale: {object_type}:{dependency.object_id}"
                )
            if getattr(current, "status", "current") in {"stale", "invalidated", "blocked", "rejected"}:
                raise DomainStateError(
                    f"engineering tool dependency is not usable: {object_type}:{dependency.object_id}"
                )

    def prepare_request(self, request: EngineeringToolRequest) -> EngineeringToolRequest:
        self._require_current_dependencies(request.dependencies)
        if request.status not in {"draft", "current"}:
            raise DomainStateError("engineering tool request must be a current draft")
        return self.registry.register("engineering_tool_request", request)

    def run_adapter(
        self,
        request: EngineeringToolRequest,
        adapter: EngineeringToolAdapter,
    ) -> RawEngineeringToolResult:
        persisted = self.repository.get_revision("engineering_tool_request", request.revision_id)
        if persisted is None:
            raise DomainStateError("engineering tool request must be persisted before execution")
        self._require_current_dependencies(request.dependencies)
        result = adapter.execute(request)
        return self.import_raw_result(result)

    def import_raw_result(self, result: RawEngineeringToolResult) -> RawEngineeringToolResult:
        request = self.repository.get_revision("engineering_tool_request", result.request_revision_id)
        if request is None:
            raise DomainStateError("raw engineering result references an unknown request revision")
        current_request = self.repository.get_current("engineering_tool_request", request.request_id)
        if current_request is None or current_request.revision_id != request.revision_id:
            raise DomainStateError("raw engineering result references a stale request")
        self._require_current_dependencies(request.dependencies)
        if (result.tool_domain, result.tool, result.tool_version) != (
            request.tool_domain,
            request.tool,
            request.tool_version,
        ):
            raise DomainStateError("raw engineering result does not match the pinned tool request")
        dependencies = tuple(dict.fromkeys((
            *result.dependencies,
            DependencyRef(
                object_type="engineering_tool_request",
                object_id=request.request_id,
                revision=request.meta.revision,
            ),
            *request.dependencies,
        )))
        persisted_result = result.model_copy(update={"dependencies": dependencies})
        return self.registry.register("raw_engineering_tool_result", persisted_result)

    def create_interpretation(
        self,
        result: RawEngineeringToolResult,
        *,
        interpretation_id: str,
        summary: str,
        findings: Iterable[str] = (),
        recommendations: Iterable[str] = (),
        limitations: Iterable[str] = (),
        structured_payload: dict[str, Any] | None = None,
        actor: str | None = None,
    ) -> EngineeringInterpretation:
        persisted = self.repository.get_revision("raw_engineering_tool_result", result.revision_id)
        if persisted is None:
            raise DomainStateError("engineering interpretation requires a persisted raw result")
        interpretation = EngineeringInterpretation(
            interpretation_id=interpretation_id,
            revision_id=f"{interpretation_id}.r1",
            meta=RevisionMeta(
                revision=1,
                created_by=actor or self.actor,
                reason="engineering result interpretation drafted",
            ),
            raw_result_revision_id=result.revision_id,
            summary=summary,
            findings=tuple(findings),
            recommendations=tuple(recommendations),
            limitations=tuple(limitations),
            structured_payload=structured_payload or {},
            status="draft",
            dependencies=(DependencyRef(
                object_type="raw_engineering_tool_result",
                object_id=result.result_id,
                revision=result.meta.revision,
            ),),
        )
        return self.registry.register("engineering_interpretation", interpretation)

    def review_interpretation(
        self,
        interpretation: EngineeringInterpretation,
        *,
        reviewer: str,
        decision: str,
        rationale: str,
        modified_summary: str | None = None,
    ) -> EngineeringInterpretation:
        if decision not in {"accepted", "modified", "rejected"}:
            raise DomainStateError("engineering interpretation review decision is invalid")
        if not is_named_human_actor(reviewer):
            raise DomainStateError("engineering interpretation requires a human reviewer")
        current = self.repository.get_current("engineering_interpretation", interpretation.interpretation_id)
        if current is None or current.revision_id != interpretation.revision_id:
            raise DomainStateError("engineering interpretation revision is stale")
        revision = current.meta.revision + 1
        reviewed = current.model_copy(update={
            "revision_id": f"{current.interpretation_id}.r{revision}",
            "meta": RevisionMeta(
                revision=revision,
                parent_revision_id=current.revision_id,
                created_by=reviewer,
                reason=rationale,
            ),
            "summary": modified_summary if decision == "modified" and modified_summary else current.summary,
            "review_decision": decision,
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc),
            "status": "approved" if decision in {"accepted", "modified"} else "rejected",
        })
        return self.registry.register("engineering_interpretation", reviewed)

    def project_reviewed_result(
        self,
        interpretation: EngineeringInterpretation,
    ) -> CADArtifact | CAEAnalysisRun | DFMReview | BOMRevision:
        current = self.repository.get_current("engineering_interpretation", interpretation.interpretation_id)
        if current is None or current.revision_id != interpretation.revision_id:
            raise DomainStateError("engineering interpretation revision is stale")
        if current.review_decision not in {"accepted", "modified"} or current.status != "approved":
            raise DomainStateError("engineering result projection requires an accepted human review")
        result = self.repository.get_revision("raw_engineering_tool_result", current.raw_result_revision_id)
        if result is None or result.execution_status == "failed":
            raise DomainStateError("engineering result projection requires usable raw output")
        request = self.repository.get_revision("engineering_tool_request", result.request_revision_id)
        if request is None:
            raise DomainStateError("engineering result request is unavailable")
        self._require_current_dependencies(request.dependencies)
        object_type = _PROJECTION_TYPES[request.tool_domain]
        existing = self.repository.get_current(object_type, request.output_object_id)
        revision = existing.meta.revision + 1 if existing is not None else 1
        revision_id = f"{request.output_object_id}.r{revision}"
        dependencies = tuple(dict.fromkeys((
            *request.dependencies,
            DependencyRef(object_type="engineering_tool_request", object_id=request.request_id, revision=request.meta.revision),
            DependencyRef(object_type="raw_engineering_tool_result", object_id=result.result_id, revision=result.meta.revision),
            DependencyRef(object_type="engineering_interpretation", object_id=current.interpretation_id, revision=current.meta.revision),
        )))
        meta = RevisionMeta(
            revision=revision,
            parent_revision_id=existing.revision_id if existing is not None else None,
            created_by=current.reviewer or "human-reviewer",
            reason="human-reviewed engineering tool result projected",
        )
        payload = dict(current.structured_payload)
        primary_artifact = result.artifacts[0] if result.artifacts else None
        common = {
            "revision_id": revision_id,
            "meta": meta,
            "dependencies": dependencies,
            "status": "approved",
            "reviewer": current.reviewer,
            "reviewed_at": current.reviewed_at,
            "assumptions": tuple(payload.get("assumptions", ())),
            "unknowns": tuple(payload.get("unknowns", ())),
            "source_refs": tuple(artifact.uri for artifact in result.artifacts),
        }
        if request.tool_domain == "cad":
            projected = CADArtifact(
                artifact_id=request.output_object_id,
                artifact_type=payload.get("artifact_type", "cad"),
                uri=primary_artifact.uri if primary_artifact else None,
                sha256=primary_artifact.sha256 if primary_artifact else None,
                format=payload.get("format", ""),
                tool=result.tool,
                tool_version=result.tool_version,
                input_revision_ids=tuple(payload.get("input_revision_ids", ())),
                **common,
            )
        elif request.tool_domain == "cae":
            convergence = result.convergence_status
            projected = CAEAnalysisRun(
                analysis_run_id=request.output_object_id,
                analysis_type=request.operation,
                solver=result.tool,
                solver_version=result.tool_version,
                boundary_conditions=dict(request.parameters),
                material_model_refs=tuple(payload.get("material_model_refs", ())),
                raw_result_uri=primary_artifact.uri if primary_artifact else None,
                convergence_status=(convergence if convergence in {"converged", "not_converged", "failed"} else "not_run"),
                uncertainty=tuple(payload.get("uncertainty", ())),
                interpretation=current.summary,
                **common,
            )
        elif request.tool_domain == "dfm":
            projected = DFMReview(
                review_id=request.output_object_id,
                cad_artifact_revision_id=payload.get("cad_artifact_revision_id"),
                manufacturability_risks=tuple(payload.get("manufacturability_risks", current.findings)),
                assembly_steps=tuple(payload.get("assembly_steps", ())),
                mold_assumptions=tuple(payload.get("mold_assumptions", ())),
                cost_assumptions=tuple(payload.get("cost_assumptions", ())),
                yield_risks=tuple(payload.get("yield_risks", ())),
                recommendation=current.summary,
                **common,
            )
        else:
            projected = BOMRevision(
                bom_id=request.output_object_id,
                part_ids=tuple(payload.get("part_ids", ())),
                parts=tuple(payload.get("parts", ())),
                supplier_assumptions=tuple(payload.get("supplier_assumptions", ())),
                cost_assumptions=tuple(payload.get("cost_assumptions", ())),
                target_cost=payload.get("target_cost"),
                currency=payload.get("currency"),
                **common,
            )
        return self.registry.register(object_type, projected)


__all__ = ["EngineeringToolAdapter", "EngineeringToolCoordinator"]
