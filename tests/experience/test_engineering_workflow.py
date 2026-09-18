from datetime import datetime, timezone
from pathlib import Path

import pytest

from psyteardown.experience import (
    CADArtifact,
    Critique,
    DesignFeedbackSelection,
    DomainStateError,
    EngineeringIntake,
    EngineeringWorkflowCoordinator,
    MaterialProcessChoice,
    MechanicalArchitecture,
    RequirementDeclaration,
    RevisionMeta,
    SQLiteExperienceRepository,
    dependency_ref,
    build_engineering_intake_from_teardown,
    DigitalExperienceDiscoveryCoordinator,
    DiscoveryTriageDecision,
)
from psyteardown.pipeline.schemas import (
    ExperienceAssessment,
    Feature,
    GroundingStats,
    Mapping,
    ProductProfile,
    TeardownMeta,
    TeardownResult,
)


NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def _teardown_result() -> TeardownResult:
    return TeardownResult(
        product=ProductProfile(
            name="Transit Anchor",
            product_type="wearable",
            one_liner="provide bounded low-distraction cancellation control",
            features=(Feature(name="cancel control", description="local cancel", user_goal="stop feedback"),),
            touchpoints=("walking", "shared transit",),
        ),
        mappings=(Mapping(
            feature="cancel control",
            framework_id="fogg",
            principle_id="prompt",
            rationale="a bounded prompt can preserve user control",
            evidence="local cancel",
            confidence=0.8,
        ),),
        grounding=GroundingStats(kept=1, dropped=0),
        assessment=ExperienceAssessment(
            friction_points=["operation may be hard while walking"],
            ethics_warnings=["shared settings may expose private content"],
            opportunities=["make cancellation explicit"],
        ),
        executive_summary="bounded control requires validation",
        meta=TeardownMeta(model="fake", generated_at="2026-09-17"),
    )


def test_teardown_discovery_becomes_reviewable_intake_signals(tmp_path: Path):
    intake = build_engineering_intake_from_teardown(
        _teardown_result(),
        project_id="discovery-project",
        scenario="walking in shared transit",
        target_segment="consented adult commuters",
    )
    assert intake.discovery_quality == "grounded"
    assert intake.declared_requirements == ()
    assert intake.ethics_risks == ("shared settings may expose private content",)
    assert intake.discovery_source_refs[0].startswith("teardown-result:")
    with SQLiteExperienceRepository(tmp_path / "discovery.db") as repo:
        project, requirements = EngineeringWorkflowCoordinator(repo).initialize_project(intake)
    discovery = tuple(item for item in requirements if "discovery" in item.requirement_id)
    assert discovery
    assert all(item.status == "draft" and item.source_type == "ai_default" for item in discovery)
    assert any(item.hard_constraint for item in discovery if "ethics" in item.requirement_id)


def test_app_discovery_requires_human_triage_before_cross_device_projection(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "triage.db") as repo:
        coordinator = DigitalExperienceDiscoveryCoordinator(repo)
        discovery = coordinator.import_teardown(
            _teardown_result(), discovery_id="app-discovery-1"
        )
        assert discovery.triage_status == "pending"
        assert len(discovery.signals) == 3
        with pytest.raises(DomainStateError, match="requires complete named-human"):
            coordinator.build_engineering_intake(
                discovery,
                project_id="cross-device-project",
                scenario="walking",
                target_segment="consented commuters",
            )
        with pytest.raises(DomainStateError, match="human reviewer"):
            coordinator.triage(
                discovery,
                decisions=tuple(
                    DiscoveryTriageDecision(
                        signal_id=item.signal_id,
                        disposition="app_experience",
                        rationale="stays in App domain",
                    )
                    for item in discovery.signals
                ),
                reviewer="ai-agent",
                rationale="automatic routing is forbidden",
            )
        with pytest.raises(DomainStateError, match="route every"):
            coordinator.triage(
                discovery,
                decisions=(),
                reviewer="experience-lead-li",
                rationale="incomplete triage",
            )
        reviewed = coordinator.triage(
            discovery,
            decisions=(
                DiscoveryTriageDecision(
                    signal_id=discovery.signals[0].signal_id,
                    disposition="device_interaction_candidate",
                    rationale="may affect no-phone cancellation",
                    candidate_statement="device should expose an explicit cancellation path",
                    validation_question="can the user cancel while walking without opening the App?",
                ),
                DiscoveryTriageDecision(
                    signal_id=discovery.signals[1].signal_id,
                    disposition="cross_channel_validation",
                    rationale="privacy spans App and device output",
                    validation_question="does any device channel expose private content in public?",
                ),
                DiscoveryTriageDecision(
                    signal_id=discovery.signals[2].signal_id,
                    disposition="app_experience",
                    rationale="remains an App opportunity",
                ),
            ),
            reviewer="experience-lead-li",
            rationale="triaged each App signal by product-domain applicability",
        )
        intake = coordinator.build_engineering_intake(
            reviewed,
            project_id="cross-device-project",
            scenario="walking in shared transit",
            target_segment="consented adult commuters",
        )
        project, requirements = EngineeringWorkflowCoordinator(repo).initialize_project(intake)
        candidates = tuple(item for item in requirements if "device-interaction" in item.requirement_id)
        assert len(candidates) == 1
        assert candidates[0].requirement_type == "explore"
        assert candidates[0].status == "draft"
        assert candidates[0].hard_constraint is False
        assert all("private content" not in item.description for item in candidates)


def test_pure_app_discovery_cannot_be_projected_to_engineering(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "app-only.db") as repo:
        coordinator = DigitalExperienceDiscoveryCoordinator(repo)
        discovery = coordinator.import_teardown(
            _teardown_result(), discovery_id="app-only-discovery"
        )
        reviewed = coordinator.triage(
            discovery,
            decisions=tuple(
                DiscoveryTriageDecision(
                    signal_id=item.signal_id,
                    disposition="app_experience",
                    rationale="only affects App/service interaction",
                )
                for item in discovery.signals
            ),
            reviewer="experience-lead-li",
            rationale="App-only scope confirmed",
        )
        with pytest.raises(DomainStateError, match="no human-routed device"):
            coordinator.build_engineering_intake(
                reviewed,
                project_id="should-not-exist",
                scenario="walking",
                target_segment="consented commuters",
            )


def _intake() -> EngineeringIntake:
    return EngineeringIntake(
        intake_id="transit-intake",
        project_id="transit-project",
        revision_id="transit-intake.r1",
        meta=RevisionMeta(revision=1, created_by="product-owner", reason="declared product intent"),
        scenario="public crowded transit while walking and boarding",
        product_purpose="provide a low-distraction wearable cancellation control",
        target_segment="consented adult commuters",
        target_markets=("CN",),
        declared_requirements=(RequirementDeclaration(
            requirement_id="req-cancel",
            title="explicit cancellation",
            description="the wearer can cancel routine feedback",
            requirement_type="must",
            acceptance_criteria=("a named test protocol verifies an explicit cancel path",),
            source="product-owner interview 2026-09-17",
            verification_methods=("physical task test",),
            verification_owner="test-lead",
            hard_constraint=True,
        ),),
    )


def test_intake_generates_sourced_requirements_and_parallel_role_tasks(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "workflow.db") as repo:
        workflow = EngineeringWorkflowCoordinator(repo)
        project, requirements = workflow.initialize_project(_intake())
        declared = next(item for item in requirements if item.requirement_id == "req-cancel")
        assert declared.source_type == "user_declared"
        assert declared.source_refs == ("product-owner interview 2026-09-17",)
        defaults = tuple(item for item in requirements if item.source_type == "ai_default")
        assert defaults
        assert all(item.assumptions and item.unknowns for item in defaults)
        assert any(item.title.startswith("Content exposure") for item in defaults)

        assert {item.task_id for item in workflow.ready_role_tasks(project)} == {
            "transit-project:requirements-review"
        }
        project, approved = workflow.approve_requirements(
            project,
            reviewer="system-engineer-li",
            rationale="sources, scope and acceptance language reviewed",
        )
        assert all(item.status == "approved" for item in approved)
        assert {item.role for item in workflow.ready_role_tasks(project)} == {
            "industrial_design", "structural_engineering", "material_process"
        }


def _experience_gate_objects(repo):
    critique = Critique(
        critique_id="critique-1",
        candidate_id="candidate-1",
        status="reviewed",
        reviewer="experience-lead",
        decision_rationale="reviewed risks and unknowns",
        revision_id="critique-1.r1",
        meta=RevisionMeta(revision=1, created_by="experience-lead", reason="reviewed"),
    )
    repo.save("critique", critique.critique_id, critique.revision_id, critique)
    selection = DesignFeedbackSelection(
        selection_id="selection-1",
        revision_id="selection-1.r1",
        meta=RevisionMeta(revision=1, created_by="product-lead", reason="human selection"),
        brief_revision_id="brief-1.r1",
        candidate_id="candidate-1",
        candidate_revision_id="candidate-1.r1",
        critique_id=critique.critique_id,
        ranked_candidate_ids=("candidate-1",),
        next_prompt_json="{}",
        actor="product-lead",
    )
    repo.save("feedback_selection", selection.selection_id, selection.revision_id, selection)
    return critique, selection


def test_stage_gate_rejects_skips_and_requires_named_engineering_evidence(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "gates.db") as repo:
        workflow = EngineeringWorkflowCoordinator(repo)
        project, _ = workflow.initialize_project(_intake())
        project, _ = workflow.approve_requirements(
            project,
            reviewer="system-engineer-li",
            rationale="requirements reviewed",
        )
        with pytest.raises(DomainStateError, match="cannot be skipped"):
            workflow.review_stage_gate(
                project,
                to_stage="engineering_ready",
                evidence_refs=(),
                reviewer="engineering-lead",
                decision="approved",
                rationale="skip attempt",
            )
        critique, selection = _experience_gate_objects(repo)
        project, _ = workflow.review_stage_gate(
            project,
            to_stage="experience_reviewed",
            evidence_refs=(
                dependency_ref("critique", critique.critique_id, 1),
                dependency_ref("feedback_selection", selection.selection_id, 1),
            ),
            reviewer="experience-lead",
            decision="approved",
            rationale="experience review complete",
        )
        assert project.stage == "experience_reviewed"
        with pytest.raises(DomainStateError, match="evidence is incomplete"):
            workflow.review_stage_gate(
                project,
                to_stage="engineering_ready",
                evidence_refs=(),
                reviewer="engineering-lead",
                decision="approved",
                rationale="missing engineering objects",
            )

        common = {
            "status": "approved",
            "reviewer": "engineering-lead",
            "reviewed_at": NOW,
        }
        mechanical = workflow.registry.register("mechanical", MechanicalArchitecture(
            architecture_id="mechanical-1",
            revision_id="mechanical-1.r1",
            meta=RevisionMeta(revision=1, created_by="structural-engineer", reason="architecture reviewed"),
            components=("housing", "internal frame"),
            interfaces=("housing-to-frame",),
            **common,
        ))
        material = workflow.registry.register("material", MaterialProcessChoice(
            choice_id="material-1",
            revision_id="material-1.r1",
            meta=RevisionMeta(revision=1, created_by="material-engineer", reason="material reviewed"),
            materials=("declared polymer grade",),
            process="injection molding assumption",
            validation_requirements=("skin contact", "aging"),
            **common,
        ))
        cad = workflow.registry.register("cad", CADArtifact(
            artifact_id="cad-1",
            revision_id="cad-1.r1",
            meta=RevisionMeta(revision=1, created_by="cad-engineer", reason="CAD reviewed"),
            uri="cad/device.step",
            sha256="a" * 64,
            format="STEP",
            tool="CAD tool",
            tool_version="2026",
            **common,
        ))
        project, gate = workflow.review_stage_gate(
            project,
            to_stage="engineering_ready",
            evidence_refs=(
                dependency_ref("mechanical", mechanical.architecture_id, 1),
                dependency_ref("material", material.choice_id, 1),
                dependency_ref("cad", cad.artifact_id, 1),
            ),
            reviewer="chief-engineer",
            decision="approved",
            rationale="interfaces and engineering objects reviewed",
        )
        assert gate.status == "approved"
        assert project.stage == "engineering_ready"


def test_hard_conflict_blocks_project_and_cannot_be_accepted_as_residual_risk(tmp_path: Path):
    with SQLiteExperienceRepository(tmp_path / "conflict.db") as repo:
        workflow = EngineeringWorkflowCoordinator(repo)
        project, requirements = workflow.initialize_project(_intake())
        requirement = next(item for item in requirements if item.requirement_id == "req-cancel")
        project, conflict = workflow.record_conflict(
            project,
            conflict_id="cancel-safety-conflict",
            title="cancel input unavailable during fault",
            description="the current architecture loses the explicit cancel path during a declared fault",
            domains=("system", "safety"),
            affected_objects=(dependency_ref("requirement", requirement.requirement_id, 1),),
            priority_class="safety",
            alternatives=("independent local stop path", "architecture revision"),
        )
        assert conflict.classification == "hard_block"
        assert project.status == "blocked"
        with pytest.raises(DomainStateError, match="cannot be accepted"):
            workflow.resolve_conflict(
                project,
                conflict,
                reviewer="safety-lead",
                disposition="accepted_risk",
                resolution="accept for schedule",
            )
        project, resolved = workflow.resolve_conflict(
            project,
            conflict,
            reviewer="safety-lead",
            disposition="resolved",
            resolution="added an independent local stop path and scheduled verification",
        )
        assert resolved.conflict_status == "resolved"
        assert project.status == "current"
        assert project.open_conflict_ids == ()
