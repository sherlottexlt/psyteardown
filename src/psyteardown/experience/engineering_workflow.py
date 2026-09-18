"""End-to-end engineering intake, role planning, conflict and stage gates."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from psyteardown.experience.engineering import (
    ENGINEERING_STAGES,
    CADArtifact,
    DFMReview,
    EngineeringConflict,
    EngineeringGateDecision,
    EngineeringIntake,
    EngineeringOrchestrator,
    EngineeringProjectRevision,
    EngineeringRequirement,
    ManufacturingReadinessReview,
    MaterialProcessChoice,
    MechanicalArchitecture,
    ReleaseDecision,
    ReliabilityCertificationReview,
    BOMRevision,
    VerificationTestRun,
    canonical_object_type,
)
from psyteardown.experience.models import DependencyRef, DomainStateError, RevisionMeta
from psyteardown.experience.multimodal import is_named_human_actor


_ROLE_PLAN = (
    ("industrial-design", "industrial_design", "create comparable form, CMF and interaction directions", ("requirements-review",)),
    ("structural-engineering", "structural_engineering", "create mechanical architecture, interfaces and tolerance risks", ("requirements-review",)),
    ("material-process", "material_process", "create material/process choices and validation requirements", ("requirements-review",)),
    ("system-integration", "system_integration", "resolve interfaces and retain Pareto alternatives", ("industrial-design", "structural-engineering", "material-process")),
    ("cae", "cae", "prepare real solver inputs and raw-result review tasks", ("system-integration",)),
    ("dfm-cost", "dfm_cost", "review manufacturability, assembly, cost and yield risks", ("system-integration",)),
    ("ergonomics-validation", "ergonomics_validation", "prepare human-factors fixtures, measures and protocols", ("system-integration",)),
    ("quality-regulatory", "quality_regulatory", "prepare FMEA, DVP&R, compliance and release gaps", ("cae", "dfm-cost", "ergonomics-validation")),
)


class EngineeringWorkflowCoordinator:
    def __init__(self, repository: Any, *, actor: str = "ai-engineering-orchestrator") -> None:
        self.repository = repository
        self.registry = EngineeringOrchestrator(repository, actor=actor)
        self.actor = actor

    def _project_current(self, project: EngineeringProjectRevision) -> EngineeringProjectRevision:
        current = self.repository.get_current("engineering_project", project.project_id)
        if current is None or current.revision_id != project.revision_id:
            raise DomainStateError("engineering project revision is stale")
        return current

    def _next_project(
        self,
        project: EngineeringProjectRevision,
        *,
        actor: str,
        reason: str,
        **updates: Any,
    ) -> EngineeringProjectRevision:
        revisions = self.repository.list_revisions("engineering_project", project.project_id)
        current = max(revisions, key=lambda item: item.meta.revision)
        revision = current.meta.revision + 1
        updated = project.model_copy(update={
            "revision_id": f"{project.project_id}.r{revision}",
            "meta": RevisionMeta(
                revision=revision,
                parent_revision_id=current.revision_id,
                created_by=actor,
                reason=reason,
            ),
            "status": "current",
            **updates,
        })
        return self.registry.register("engineering_project", updated, auto_invalidate=False)

    def _default_requirements(self, intake: EngineeringIntake) -> tuple[EngineeringRequirement, ...]:
        base = f"{intake.project_id}-req"
        declared_ids = {item.requirement_id for item in intake.declared_requirements}
        requirements: list[EngineeringRequirement] = []
        for declaration in intake.declared_requirements:
            requirements.append(EngineeringRequirement(
                requirement_id=declaration.requirement_id,
                revision_id=f"{declaration.requirement_id}.r1",
                meta=RevisionMeta(revision=1, created_by=intake.meta.created_by, reason="declared engineering requirement"),
                status="draft",
                title=declaration.title,
                description=declaration.description,
                requirement_type=declaration.requirement_type,
                acceptance_criteria=declaration.acceptance_criteria,
                priority=declaration.priority,
                applicable_scope=declaration.applicable_scope or (intake.scenario,),
                verification_methods=declaration.verification_methods,
                source_type=declaration.source_type,
                source_refs=(declaration.source,),
                verification_owner=declaration.verification_owner,
                hard_constraint=declaration.hard_constraint,
                dependencies=(DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),),
            ))

        defaults = (
            (
                f"{base}-core-function", "Core function within declared use", "must",
                (f"Verify the declared product purpose under the scoped scenario: {intake.product_purpose}",),
                ("functional verification protocol",), True, "system-engineer",
            ),
            (
                f"{base}-safety", "Safety risks identified and controlled", "must",
                ("Every identified high-severity hazard has an owner, mitigation and physical verification plan.",),
                ("risk review", "physical verification"), True, "safety-engineer",
            ),
            (
                f"{base}-ergonomics", "Human-factors performance is measured", "should",
                ("A scoped participant protocol records fit, operation, error recovery and cancellation measurements.",),
                ("human-factors study",), False, "human-factors-engineer",
            ),
            (
                f"{base}-maintainability", "Assembly and maintenance path is explicit", "should",
                ("BOM, assembly sequence, service access and replacement assumptions are reviewed.",),
                ("DFM review", "service review"), False, "manufacturing-engineer",
            ),
        )
        for req_id, title, req_type, criteria, methods, hard, owner in defaults:
            if req_id in declared_ids:
                continue
            requirements.append(EngineeringRequirement(
                requirement_id=req_id,
                revision_id=f"{req_id}.r1",
                meta=RevisionMeta(revision=1, created_by=self.actor, reason="AI-default requirement awaiting human review"),
                status="draft",
                title=title,
                description=f"Default generated from scenario '{intake.scenario}' and purpose '{intake.product_purpose}'.",
                requirement_type=req_type,
                acceptance_criteria=criteria,
                priority=1 if req_type == "must" else 2,
                applicable_scope=(intake.scenario,),
                verification_methods=methods,
                source_type="ai_default",
                source_refs=(f"engineering_intake:{intake.revision_id}",),
                verification_owner=owner,
                hard_constraint=hard,
                assumptions=("AI-default requirement; a named system engineer must confirm scope and threshold values.",),
                unknowns=("Numeric threshold is not inferred without user, regulation or measured evidence.",),
                dependencies=(DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),),
            ))
        # Raw App teardown friction/ethics/opportunity text never enters the
        # requirement registry directly.  Only device-interaction candidates
        # explicitly routed by named-human discovery triage reach this point.
        for index, candidate in enumerate(intake.device_interaction_candidates, start=1):
            req_id = f"{base}-device-interaction-{index}"
            requirements.append(EngineeringRequirement(
                requirement_id=req_id,
                revision_id=f"{req_id}.r1",
                meta=RevisionMeta(revision=1, created_by=self.actor, reason="triaged device-interaction candidate awaiting system-engineering review"),
                status="draft",
                title=f"Validate device-interaction candidate: {candidate[:90]}",
                description=candidate,
                requirement_type="explore",
                acceptance_criteria=("A named system engineer defines the applicable scope, threshold and cross-device verification protocol.",),
                priority=2,
                applicable_scope=(intake.scenario,),
                verification_methods=("cross-device interaction prototype test",),
                source_type="ai_default",
                source_refs=tuple(dict.fromkeys((*intake.discovery_source_refs, *intake.source_refs))),
                verification_owner="interaction-system-engineer",
                hard_constraint=False,
                assumptions=("A named discovery reviewer routed this App signal to device-interaction exploration.",),
                unknowns=("It is not yet established that the candidate is a product requirement or that hardware is the correct intervention.",),
                dependencies=(DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),),
            ))
        # Migration-only compatibility for the old direct bridge. New
        # ``discovery`` CLI flows never set this marker and therefore cannot
        # promote raw App signals into engineering requirements.
        if intake.legacy_direct_discovery:
            signal_groups = (
                ("risk", intake.experience_risks, "should", False, "human-factors-engineer"),
                ("ethics", intake.ethics_risks, "must", True, "quality-regulatory"),
                ("opportunity", intake.experience_opportunities, "should", False, "system-engineer"),
            )
            for group, signals, req_type, hard, owner in signal_groups:
                for index, signal in enumerate(signals, start=1):
                    req_id = f"{base}-discovery-{group}-{index}"
                    requirements.append(EngineeringRequirement(
                        requirement_id=req_id,
                        revision_id=f"{req_id}.r1",
                        meta=RevisionMeta(revision=1, created_by=self.actor, reason="deprecated direct discovery compatibility"),
                        status="draft",
                        title=f"[deprecated] Review discovery {group}: {signal[:90]}",
                        description=f"Legacy direct bridge signal; migrate through discovery triage: {signal}",
                        requirement_type=req_type,
                        acceptance_criteria=("Migrate this signal through named-human discovery triage before using it for engineering decisions.",),
                        priority=1 if hard else 2,
                        applicable_scope=(intake.scenario,),
                        verification_methods=("discovery triage",),
                        source_type="ai_default",
                        source_refs=tuple(dict.fromkeys((*intake.discovery_source_refs, *intake.source_refs))),
                        verification_owner=owner,
                        hard_constraint=hard,
                        assumptions=("Deprecated compatibility object; not a reviewed requirement.",),
                        unknowns=("The App signal has not been triaged for product-domain applicability.",),
                        dependencies=(DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),),
                    ))
        context = intake.scenario.lower()
        if any(token in context for token in ("public", "shared", "crowd", "transit", "公共", "共享", "通勤", "拥挤")):
            req_id = f"{base}-privacy"
            if req_id not in declared_ids:
                requirements.append(EngineeringRequirement(
                    requirement_id=req_id,
                    revision_id=f"{req_id}.r1",
                    meta=RevisionMeta(revision=1, created_by=self.actor, reason="AI-default public-context privacy requirement"),
                    status="draft",
                    title="Content exposure is bounded in shared settings",
                    description="The scenario appears shared/public; this remains an explicit default assumption.",
                    requirement_type="must",
                    acceptance_criteria=("A privacy review verifies that routine feedback does not expose private content to bystanders.",),
                    applicable_scope=(intake.scenario,),
                    verification_methods=("privacy review", "scenario test"),
                    source_type="ai_default",
                    source_refs=(f"engineering_intake:{intake.revision_id}",),
                    verification_owner="privacy-reviewer",
                    hard_constraint=True,
                    assumptions=("AI classified the declared scenario as potentially shared/public; human confirmation is required.",),
                    unknowns=("Applicable privacy threshold and test condition are not yet confirmed.",),
                    dependencies=(DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),),
                ))
        return tuple(requirements)

    def initialize_project(
        self,
        intake: EngineeringIntake,
    ) -> tuple[EngineeringProjectRevision, tuple[EngineeringRequirement, ...]]:
        if self.repository.get_current("engineering_project", intake.project_id) is not None:
            raise DomainStateError("engineering project already exists")
        self.registry.register("engineering_intake", intake)
        requirements = self._default_requirements(intake)
        for requirement in requirements:
            self.registry.register("engineering_requirement", requirement)

        prefix = intake.project_id
        review_task_id = f"{prefix}:requirements-review"
        self.registry.create_task(
            task_id=review_task_id,
            role="system_engineering",
            action="review sources, assumptions, acceptance criteria and hard constraints",
            dependencies=(DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),),
            human_gate_required=True,
        )
        role_task_ids = [review_task_id]
        for suffix, role, action, predecessors in _ROLE_PLAN:
            task_id = f"{prefix}:{suffix}"
            role_task_ids.append(task_id)
            self.registry.create_task(
                task_id=task_id,
                role=role,
                action=action,
                depends_on_task_ids=tuple(f"{prefix}:{item}" for item in predecessors),
                human_gate_required=role == "quality_regulatory",
            )
        project = EngineeringProjectRevision(
            project_id=intake.project_id,
            revision_id=f"{intake.project_id}.r1",
            meta=RevisionMeta(revision=1, created_by=self.actor, reason="engineering project initialized"),
            dependencies=(
                DependencyRef(object_type="engineering_intake", object_id=intake.intake_id, revision=intake.meta.revision),
                *(DependencyRef(object_type="engineering_requirement", object_id=item.requirement_id, revision=item.meta.revision) for item in requirements),
            ),
            status="draft",
            intake_revision_id=intake.revision_id,
            scenario=intake.scenario,
            product_purpose=intake.product_purpose,
            requirement_revision_ids=tuple(item.revision_id for item in requirements),
            role_task_ids=tuple(role_task_ids),
        )
        return self.registry.register("engineering_project", project), requirements

    def approve_requirements(
        self,
        project: EngineeringProjectRevision,
        *,
        reviewer: str,
        rationale: str,
    ) -> tuple[EngineeringProjectRevision, tuple[EngineeringRequirement, ...]]:
        self._project_current(project)
        if not is_named_human_actor(reviewer):
            raise DomainStateError("requirements approval requires a named human reviewer")
        approved: list[EngineeringRequirement] = []
        now = datetime.now(timezone.utc)
        for revision_id in project.requirement_revision_ids:
            requirement = self.repository.get_revision("engineering_requirement", revision_id)
            if requirement is None:
                raise DomainStateError("project requirement revision is unavailable")
            current = self.repository.get_current("engineering_requirement", requirement.requirement_id)
            if current is None or current.revision_id != requirement.revision_id:
                raise DomainStateError("project requirement revision is stale")
            revision = current.meta.revision + 1
            item = current.model_copy(update={
                "revision_id": f"{current.requirement_id}.r{revision}",
                "meta": RevisionMeta(revision=revision, parent_revision_id=current.revision_id, created_by=reviewer, reason=rationale),
                "status": "approved",
                "reviewer": reviewer,
                "reviewed_at": now,
            })
            self.registry.register("engineering_requirement", item)
            approved.append(item)
        review_task = self.repository.get_current("engineering_task", f"{project.project_id}:requirements-review")
        if review_task is None:
            raise DomainStateError("requirements review task is unavailable")
        if review_task.status in {"stale", "invalidated"}:
            raise DomainStateError("requirements review task is stale")
        self.registry.update_task(review_task, status="completed", result_revision_ids=(item.revision_id for item in approved), actor=reviewer)
        approved_refs = tuple(
            DependencyRef(object_type="engineering_requirement", object_id=item.requirement_id, revision=item.meta.revision)
            for item in approved
        )
        # Pin every professional task to the approved requirement revisions.
        # A later requirement change therefore makes pending or completed
        # discipline work stale instead of silently reusing it.
        for task_id in project.role_task_ids:
            if task_id.endswith(":requirements-review"):
                continue
            task = self.repository.get_current("engineering_task", task_id)
            if task is None:
                raise DomainStateError(f"engineering role task is unavailable: {task_id}")
            revision = task.meta.revision + 1
            revised_task = task.model_copy(update={
                "revision_id": f"{task.task_id}.r{revision}",
                "meta": RevisionMeta(
                    revision=revision,
                    parent_revision_id=task.revision_id,
                    created_by=reviewer,
                    reason="approved requirement revisions pinned to role task",
                ),
                "dependencies": tuple(dict.fromkeys((*task.dependencies, *approved_refs))),
                "status": "current",
            })
            self.registry.register("engineering_task", revised_task, auto_invalidate=False)
        intake_ref = next(
            (item for item in project.dependencies if item.object_type == "engineering_intake"),
            None,
        )
        if intake_ref is None:
            raise DomainStateError("engineering project is missing its intake dependency")
        current_intake = self.repository.get_current("engineering_intake", intake_ref.object_id)
        if current_intake is None or current_intake.meta.revision != intake_ref.revision:
            raise DomainStateError("engineering project intake revision is stale")
        updated = self._next_project(
            project,
            actor=reviewer,
            reason=rationale,
            requirement_revision_ids=tuple(item.revision_id for item in approved),
            dependencies=(
                intake_ref,
                *(DependencyRef(object_type="engineering_requirement", object_id=item.requirement_id, revision=item.meta.revision) for item in approved),
            ),
        )
        return updated, tuple(approved)

    def ready_role_tasks(self, project: EngineeringProjectRevision):
        current = self.repository.get_current("engineering_project", project.project_id)
        if current is None:
            raise DomainStateError("engineering project is unavailable")
        allowed = set(current.role_task_ids)
        return tuple(task for task in self.registry.ready_tasks() if task.task_id in allowed)

    def _resolve_gate_refs(self, refs: Iterable[DependencyRef]) -> tuple[tuple[DependencyRef, Any], ...]:
        resolved: list[tuple[DependencyRef, Any]] = []
        for ref in refs:
            object_type = canonical_object_type(ref.object_type)
            current = self.repository.get_current(object_type, ref.object_id)
            if current is None or current.meta.revision != ref.revision:
                raise DomainStateError(f"stage gate reference is unavailable or stale: {object_type}:{ref.object_id}")
            resolved.append((ref, current))
        return tuple(resolved)

    def _stage_issues(self, to_stage: str, resolved: tuple[tuple[DependencyRef, Any], ...]) -> tuple[str, ...]:
        values = tuple(item for _, item in resolved)
        issues: list[str] = []
        if to_stage == "experience_reviewed":
            critiques = tuple(item for item in values if type(item).__name__ == "Critique")
            selections = tuple(item for item in values if type(item).__name__ == "DesignFeedbackSelection")
            if not critiques or any(item.status not in {"reviewed", "approved"} or not item.reviewer for item in critiques):
                issues.append("experience_critique_not_human_reviewed")
            if not selections or any(item.status != "confirmed" for item in selections):
                issues.append("m3_selection_not_confirmed")
        elif to_stage == "engineering_ready":
            required = (MechanicalArchitecture, MaterialProcessChoice, CADArtifact)
            for model in required:
                matches = tuple(item for item in values if isinstance(item, model))
                if not matches or any(item.status != "approved" or not item.reviewer for item in matches):
                    issues.append(f"{model.__name__}_not_approved")
        elif to_stage == "prototype_ready":
            for model in (BOMRevision, DFMReview):
                matches = tuple(item for item in values if isinstance(item, model))
                if not matches or any(item.status != "approved" or not item.reviewer for item in matches):
                    issues.append(f"{model.__name__}_not_approved")
        elif to_stage == "physical_validation":
            runs = tuple(item for item in values if type(item).__name__ == "PrototypeRun")
            reviews = tuple(item for item in values if type(item).__name__ == "EvidenceReview")
            if not runs:
                issues.append("prototype_run_missing")
            if not reviews or any(item.decision not in {"accepted", "modified", "confirmed"} or item.evidence_level_after == "none" for item in reviews):
                issues.append("evidence_review_not_accepted")
        elif to_stage == "compliance_reviewed":
            matches = tuple(item for item in values if isinstance(item, ReliabilityCertificationReview))
            if not matches or any(item.decision != "approved" or item.status != "approved" for item in matches):
                issues.append("compliance_not_approved")
        elif to_stage == "manufacturing_ready":
            matches = tuple(item for item in values if isinstance(item, ManufacturingReadinessReview))
            if not matches or any(item.readiness != "ready" or item.status != "approved" for item in matches):
                issues.append("manufacturing_readiness_not_ready")
        elif to_stage == "released":
            matches = tuple(item for item in values if isinstance(item, ReleaseDecision))
            if not matches or any(item.decision != "approved" or item.status != "approved" for item in matches):
                issues.append("release_decision_not_approved")
        return tuple(issues)

    def review_stage_gate(
        self,
        project: EngineeringProjectRevision,
        *,
        to_stage: str,
        evidence_refs: Iterable[DependencyRef],
        reviewer: str,
        decision: str,
        rationale: str,
    ) -> tuple[EngineeringProjectRevision, EngineeringGateDecision]:
        project = self._project_current(project)
        if not is_named_human_actor(reviewer):
            raise DomainStateError("engineering stage gate requires a named human reviewer")
        current_index = ENGINEERING_STAGES.index(project.stage)
        if current_index + 1 >= len(ENGINEERING_STAGES) or ENGINEERING_STAGES[current_index + 1] != to_stage:
            raise DomainStateError("engineering stages cannot be skipped")
        refs = tuple(evidence_refs)
        resolved = self._resolve_gate_refs(refs)
        issues = list(self._stage_issues(to_stage, resolved))
        if project.open_conflict_ids:
            issues.append("open_engineering_conflicts")
        current_requirements = tuple(
            self.repository.get_current("engineering_requirement", revision_id.rsplit(".r", 1)[0])
            for revision_id in project.requirement_revision_ids
        )
        if not current_requirements or any(
            item is None or item.status != "approved" or not item.reviewer
            for item in current_requirements
        ):
            issues.append("requirements_not_human_approved")
        issues = tuple(dict.fromkeys(issues))
        if decision == "approved" and issues:
            raise DomainStateError("stage gate evidence is incomplete: " + ", ".join(issues))
        if decision not in {"approved", "blocked", "conditional"}:
            raise DomainStateError("stage gate decision is invalid")
        gate = self.registry.approve_gate(
            target_object_type="engineering_project",
            target_object_id=project.project_id,
            target_revision_id=project.revision_id,
            from_stage=project.stage,
            to_stage=to_stage,
            reviewer=reviewer,
            evidence_refs=tuple(
                f"{canonical_object_type(ref.object_type)}:{ref.object_id}:r{ref.revision}" for ref in refs
            ),
            rationale=(rationale if not issues else rationale + "; issues: " + ", ".join(issues)),
            decision=decision,
            actor=reviewer,
        )
        if decision != "approved":
            return project, gate
        updated = self._next_project(
            project,
            actor=reviewer,
            reason=rationale,
            stage=to_stage,
            gate_decision_revision_ids=(*project.gate_decision_revision_ids, gate.revision_id),
            dependencies=tuple(dict.fromkeys((*project.dependencies, *refs))),
        )
        return updated, gate

    def record_conflict(
        self,
        project: EngineeringProjectRevision,
        *,
        conflict_id: str,
        title: str,
        description: str,
        domains: Iterable[str],
        affected_objects: Iterable[DependencyRef],
        priority_class: str,
        alternatives: Iterable[str] = (),
        actor: str | None = None,
    ) -> tuple[EngineeringProjectRevision, EngineeringConflict]:
        project = self._project_current(project)
        if priority_class in {"safety", "regulatory", "core_function"}:
            classification = "hard_block"
            status = "blocked"
        elif priority_class == "unknown":
            classification = "human_decision_required"
            status = "pending"
        else:
            classification = "pareto_tradeoff"
            status = "pending"
        affected = tuple(affected_objects)
        self._resolve_gate_refs(affected)
        conflict = EngineeringConflict(
            conflict_id=conflict_id,
            revision_id=f"{conflict_id}.r1",
            meta=RevisionMeta(revision=1, created_by=actor or self.actor, reason="engineering conflict recorded"),
            dependencies=affected,
            status=status,
            title=title,
            description=description,
            domains=tuple(domains),
            affected_objects=affected,
            priority_class=priority_class,
            classification=classification,
            alternatives=tuple(alternatives),
        )
        self.registry.register("engineering_conflict", conflict)
        task_id = f"{project.project_id}:resolve:{conflict_id}"
        self.registry.create_task(
            task_id=task_id,
            role="system_integration",
            action=f"resolve {classification} conflict: {title}",
            dependencies=(DependencyRef(object_type="engineering_conflict", object_id=conflict_id, revision=1),),
            human_gate_required=True,
        )
        updated = self._next_project(
            project,
            actor=actor or self.actor,
            reason="engineering conflict attached",
            status="blocked" if classification == "hard_block" else project.status,
            open_conflict_ids=tuple(dict.fromkeys((*project.open_conflict_ids, conflict_id))),
            role_task_ids=(*project.role_task_ids, task_id),
            dependencies=tuple(dict.fromkeys((*project.dependencies, DependencyRef(object_type="engineering_conflict", object_id=conflict_id, revision=1)))),
        )
        return updated, conflict

    def resolve_conflict(
        self,
        project: EngineeringProjectRevision,
        conflict: EngineeringConflict,
        *,
        reviewer: str,
        disposition: str,
        resolution: str,
    ) -> tuple[EngineeringProjectRevision, EngineeringConflict]:
        project = self._project_current(project)
        if not is_named_human_actor(reviewer):
            raise DomainStateError("engineering conflict resolution requires a named human reviewer")
        current = self.repository.get_current("engineering_conflict", conflict.conflict_id)
        if current is None or current.revision_id != conflict.revision_id:
            raise DomainStateError("engineering conflict revision is stale")
        if disposition not in {"resolved", "accepted_risk", "rejected"}:
            raise DomainStateError("engineering conflict disposition is invalid")
        if conflict.classification == "hard_block" and disposition == "accepted_risk":
            raise DomainStateError("safety, regulatory or core-function conflicts cannot be accepted as residual risk")
        revision = conflict.meta.revision + 1
        reviewed = conflict.model_copy(update={
            "revision_id": f"{conflict.conflict_id}.r{revision}",
            "meta": RevisionMeta(revision=revision, parent_revision_id=conflict.revision_id, created_by=reviewer, reason=resolution),
            "status": "approved" if disposition == "resolved" else "rejected",
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc),
            "conflict_status": disposition,
            "resolution": resolution,
        })
        self.registry.register("engineering_conflict", reviewed)
        updated = self._next_project(
            project,
            actor=reviewer,
            reason="engineering conflict resolved",
            status="current",
            open_conflict_ids=tuple(item for item in project.open_conflict_ids if item != conflict.conflict_id),
            dependencies=tuple(
                dep for dep in project.dependencies
                if not (dep.object_type == "engineering_conflict" and dep.object_id == conflict.conflict_id)
            ) + (DependencyRef(object_type="engineering_conflict", object_id=conflict.conflict_id, revision=reviewed.meta.revision),),
        )
        return updated, reviewed


__all__ = ["EngineeringWorkflowCoordinator"]
