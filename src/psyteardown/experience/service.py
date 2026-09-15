"""Application commands for the structured-text/fake-provider vertical slice."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import uuid4

from psyteardown.experience.models import (
    AuditEvent,
    CandidateFactsSnapshot,
    CandidatePartialOrder,
    ClaimJudgement,
    DesignBrief,
    DesignCandidate,
    DesignIteration,
    DesignToolRun,
    PrototypeRun,
    PrototypeAsset,
    ExternalAsset,
    ObservationDraft,
    ConfirmedObservation,
    DependencyRef,
    MeasurementObservation,
    EvidenceReview,
    ScenarioPolicy,
    FutureMovementScenario,
    DomainEvent,
    DomainStateError,
    IssueImprovement,
    IterationStatus,
    NextDesignPrompt,
    ProgressiveDesignModel,
    PatchApplicationTrace,
    ReviewItem,
    ReviewItemDraft,
    RevisionMeta,
    SelectionDecision,
    VariablePatch,
    VariableRepairTrace,
    UnauthorizedOutput,
    ContaminationMark,
    CleanRerunClosure,
    CleanRerunRecord,
)
from psyteardown.experience.providers import ClaimJudge, DesignGenerator, ReviewReasoner
from psyteardown.experience.repositories import InMemoryExperienceRepository
from psyteardown.experience.adapters import DesignToolRequest, DesignToolResult, attach_design_tool_result
from psyteardown.experience.iteration import (
    apply_variable_patches_to_candidate,
    create_patched_progressive_model,
    canonical_variable_id,
)
from psyteardown.experience.rules import (
    aggregate_evaluation,
    build_candidate,
    build_partial_order,
    check_batch_divergence,
    freeze_candidate_facts,
    find_patch_conflicts,
    validate_brief_for_freeze,
)
from psyteardown.experience.mobility import build_scenario_policy
from psyteardown.experience.contamination import (
    quarantine_output as build_quarantine_output,
    propagate_contamination as build_contamination_mark,
    build_clean_rerun,
)
from psyteardown.experience.research import ResearchApplicationService
from psyteardown.experience.experiment_planner import build_experiment_plan, preregister_plan
from psyteardown.experience.m3_feedback import (
    build_feedback_selection,
    run_feedback_loop,
    select_feedback_candidate,
)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class ExperienceApplicationService:
    def __init__(
        self,
        repository: InMemoryExperienceRepository | None = None,
        *,
        design_generator: DesignGenerator | None = None,
        review_reasoner: ReviewReasoner | None = None,
        claim_judge: ClaimJudge | None = None,
    ) -> None:
        self.repository = repository or InMemoryExperienceRepository()
        self.design_generator = design_generator
        self.review_reasoner = review_reasoner
        self.claim_judge = claim_judge

    # ----- generic M1 research records -------------------------------------
    # Kept as aliases on the established application service so callers do
    # not need to know whether they are using the prototype or generic slice.
    def save_evidence(self, evidence, *, expected_revision: int | None = None):
        return ResearchApplicationService(self.repository).save_evidence(evidence, expected_revision=expected_revision)

    def save_observation(self, observation, *, expected_revision: int | None = None):
        return ResearchApplicationService(self.repository).save_observation(observation, expected_revision=expected_revision)

    def save_hypothesis(self, hypothesis, *, expected_revision: int | None = None):
        return ResearchApplicationService(self.repository).save_hypothesis(hypothesis, expected_revision=expected_revision)

    def save_critique(self, critique, *, expected_revision: int | None = None):
        return ResearchApplicationService(self.repository).save_critique(critique, expected_revision=expected_revision)

    def create_experiment_plan(self, hypothesis, **kwargs):
        """Generate and persist an M2 draft plan from a conditional hypothesis."""
        plan = build_experiment_plan(hypothesis, **kwargs)
        self.repository.save("experiment_plan", plan.experiment_id, plan.revision_id, plan)
        return plan

    def preregister_experiment_plan(self, plan, *, actor: str = "human"):
        """Persist a human-approved preregistered revision."""
        updated = preregister_plan(plan, actor=actor)
        self.repository.save("experiment_plan", updated.experiment_id, updated.revision_id, updated)
        return updated

    def run_design_feedback(self, brief: DesignBrief, *, generator, n: int | None = None, actor: str = "system"):
        """Persist an M3 generated candidate/critique bundle without selecting it."""
        result = run_feedback_loop(brief, generator=generator, n=n, actor=actor)
        for candidate in result.candidates:
            self.repository.save("candidate", candidate.candidate_id, candidate.candidate_revision_id, candidate)
        for critique in result.critiques:
            self.repository.save("critique", critique.critique_id, critique.revision_id, critique)
        # When the brief is already frozen, attach the bundle to the normal
        # iteration aggregate.  Draft briefs remain export-only until a human
        # freezes them through the existing command boundary.
        if brief.status == "frozen":
            iteration = self.create_iteration(brief, round_number=1, actor=actor)
            iteration = self._advance_iteration(
                iteration,
                actor=actor,
                reason="M3 feedback candidates imported",
                status=IterationStatus.CANDIDATES_IMPORTED,
                candidate_revision_ids=tuple(item.candidate_revision_id for item in result.candidates),
                divergence_gaps=check_batch_divergence(result.candidates, brief),
            )
            result = result.__class__(
                **{**result.__dict__, "iteration_id": iteration.iteration_id}
            )
        return result

    def select_design_feedback(self, brief: DesignBrief, result, candidate_id: str, *, actor: str = "human"):
        """Persist an explicit M3 selection and its prompt projection."""
        updated = select_feedback_candidate(brief, result, candidate_id, actor=actor)
        selection = build_feedback_selection(updated, actor=actor)
        self.repository.save("feedback_selection", selection.selection_id, selection.revision_id, selection)
        return updated, selection

    # ----- contamination / clean-rerun boundary ----------------------------
    def quarantine_output(self, **kwargs) -> UnauthorizedOutput:
        """Persist an unauthorized output as quarantined, even if unviewed."""
        actor = kwargs.pop("actor", "system")
        output = build_quarantine_output(**kwargs)
        self.repository.save("unauthorized_output", output.output_id, output.revision_id, output)
        self._record(event_type="UnauthorizedOutputQuarantined", aggregate_id=output.output_id, revision_id=output.revision_id, actor=actor, reason="unauthorized output isolated")
        return output

    def mark_contamination(self, **kwargs) -> ContaminationMark:
        actor = kwargs.pop("actor", "system")
        mark = build_contamination_mark(**kwargs)
        self.repository.save("contamination_mark", mark.object_id, mark.revision_id, mark)
        self._record(event_type="UnauthorizedOutputContaminated", aggregate_id=mark.object_id, revision_id=mark.revision_id, actor=actor, reason="contamination propagated through lineage")
        return mark

    def record_clean_rerun(self, **kwargs) -> CleanRerunRecord:
        actor = kwargs.pop("actor", "system")
        rerun = build_clean_rerun(**kwargs)
        # Divergent or uncertain reruns are retained for analysis only.  A
        # clean rederivation may be current as a new revision, but this does
        # not infer any post-428 selection qualification.
        current = rerun.status == "clean_rederived"
        self.repository.save("clean_rerun", rerun.rerun_id, rerun.revision_id, rerun, current=current)
        self._record(event_type="CleanRerunRecorded", aggregate_id=rerun.rerun_id, revision_id=rerun.revision_id, actor=actor, reason=rerun.status)
        return rerun

    # Explicit command names used by callers that model the workflow as a
    # command bus.  These delegate to the same guarded implementations.
    def freeze_design_brief(self, brief: DesignBrief, **kwargs) -> DesignBrief:
        return self.freeze_brief(brief, **kwargs)

    def freeze_candidate_facts(self, candidate: DesignCandidate, **kwargs) -> CandidateFactsSnapshot:
        return self.freeze_facts(candidate, **kwargs)

    def confirm_review(self, facts: CandidateFactsSnapshot, draft: ReviewItemDraft, judgement: ClaimJudgement, **kwargs) -> ReviewItem:
        return self.confirm_review_item(facts, draft, judgement, **kwargs)

    def create_partial_order(self, iteration: DesignIteration, **kwargs) -> CandidatePartialOrder:
        return self.compare_candidates(iteration, **kwargs)

    def build_next_prompt(self, iteration: DesignIteration, decision: SelectionDecision, **kwargs) -> NextDesignPrompt:
        return self.confirm_next_prompt(iteration, decision, **kwargs)

    def track_variable_repair(self, parent: DesignCandidate, child: DesignCandidate, patches: tuple[VariablePatch, ...], **kwargs) -> VariableRepairTrace:
        return self.build_variable_repair_trace(parent, child, patches, **kwargs)

    def apply_variable_patch_revision(
        self,
        parent: DesignCandidate,
        model: ProgressiveDesignModel,
        patches: tuple[VariablePatch, ...],
        *,
        actor: str = "system",
    ) -> tuple[DesignCandidate, ProgressiveDesignModel, VariableRepairTrace]:
        """Project confirmed review patches into immutable child snapshots.

        The child is deliberately stored as a separate candidate revision and
        the model's render/geometry layers are reset until a fresh provider
        result is reviewed.  A repair trace compares the child facts with the
        patch targets, preserving partial/non-adoption rather than claiming
        success from a generator declaration.
        """
        if model.candidate_revision_id != parent.candidate_revision_id:
            raise DomainStateError("progressive model does not belong to parent candidate")
        patches = tuple(
            patch.model_copy(
                update={
                    "variable_id": canonical_variable_id(patch.variable_id),
                    "from_value": patch.from_value.model_copy(update={"variable_id": canonical_variable_id(patch.from_value.variable_id)}) if patch.from_value else None,
                    "to_value": patch.to_value.model_copy(update={"variable_id": canonical_variable_id(patch.to_value.variable_id)}) if patch.to_value else None,
                }
            )
            for patch in patches
        )
        child = apply_variable_patches_to_candidate(parent, patches, actor=actor)
        # Branching from the same parent is allowed.  Allocate the next
        # aggregate revision from persisted history instead of assuming the
        # parent pointer is the latest branch (which would collide in SQLite).
        existing_models = [
            value
            for value in self.repository.list_revisions("progressive_model")
            if value.model_id == model.model_id
        ]
        next_model_revision = max((value.meta.revision for value in existing_models), default=model.meta.revision) + 1
        child_model = create_patched_progressive_model(
            model, child, patches, actor=actor, revision=next_model_revision
        )
        for patch in patches:
            if self.repository.get_revision("patch", patch.revision_id) is None:
                self.repository.save("patch", patch.patch_id, patch.revision_id, patch)
        existing_child = self.repository.get_revision("candidate", child.candidate_revision_id)
        if existing_child is not None:
            child = existing_child
        else:
            self.repository.save("candidate", child.candidate_id, child.candidate_revision_id, child)
        self.repository.save("progressive_model", child_model.model_id, child_model.revision_id, child_model)
        patch_ids = {patch.revision_id for patch in patches}
        trace = next(
            (
                value
                for value in self.repository.list_revisions("repair_trace")
                if value.parent_candidate_revision_id == parent.candidate_revision_id
                and value.child_candidate_revision_id == child.candidate_revision_id
                and {item.patch_revision_id for item in value.patch_applications} == patch_ids
            ),
            None,
        )
        if trace is None:
            trace = self.build_variable_repair_trace(parent, child, patches, actor=actor)
        self._record(
            event_type="VariablePatchRevisionCreated",
            aggregate_id=child.candidate_id,
            revision_id=child.candidate_revision_id,
            actor=actor,
            reason="confirmed VariablePatch projected into child candidate",
            data={"parent_revision_id": parent.candidate_revision_id, "model_revision_id": child_model.revision_id},
        )
        self._record(
            event_type="ProgressiveDesignModelRevisionCreated",
            aggregate_id=child_model.model_id,
            revision_id=child_model.revision_id,
            actor=actor,
            reason="render and geometry invalidated for parameterized revision",
            data={"candidate_revision_id": child.candidate_revision_id},
        )
        return child, child_model, trace

    def attach_design_tool_result(
        self,
        model: "ProgressiveDesignModel",
        result: DesignToolResult,
        *,
        actor: str = "human",
        confirmed: bool = False,
        request: DesignToolRequest | None = None,
    ) -> "ProgressiveDesignModel":
        """Create and persist a new progressive-model revision.

        Unconfirmed provider results are retained only as a draft dependency;
        render/geometry layers remain missing until ``confirmed=True``.
        """

        if result.candidate_revision_id != model.candidate_revision_id:
            raise DomainStateError("design-tool result is stale for the current candidate revision")
        if request is not None:
            if request.candidate_revision_id != model.candidate_revision_id:
                raise DomainStateError("design-tool request belongs to another candidate revision")
            if result.request_id != request.request_id:
                raise DomainStateError("design-tool result does not match the persisted request")
            if request.parent_model_revision_id and request.parent_model_revision_id not in {model.revision_id, model.meta.parent_revision_id}:
                raise DomainStateError("design-tool request is stale for the current model revision")
            if request.patch_revision_ids and not set(request.patch_revision_ids).issubset(set(model.applied_patch_revision_ids)):
                raise DomainStateError("design-tool request references patches not applied to the current model")
        updated = attach_design_tool_result(model, result, actor=actor, confirmed=confirmed)
        if request is not None:
            run_id = _id("design-tool-run")
            run = DesignToolRun(
                run_id=run_id,
                revision_id=f"{run_id}.r1",
                meta=RevisionMeta(revision=1, created_by=actor, reason="design-tool request/result recorded"),
                candidate_revision_id=result.candidate_revision_id,
                parent_model_revision_id=request.parent_model_revision_id or model.revision_id,
                resulting_model_revision_id=updated.revision_id,
                patch_revision_ids=tuple(request.patch_revision_ids),
                request_json=request.model_dump(mode="json"),
                result_json=result.model_dump(mode="json"),
                confirmation="confirmed" if confirmed else "pending",
            )
            self.repository.save("design_tool_run", run.run_id, run.revision_id, run)
            self._record(
                event_type="DesignToolRunRecorded",
                aggregate_id=run.run_id,
                revision_id=run.revision_id,
                actor=actor,
                reason="human-confirmed design-tool run" if confirmed else "provider draft design-tool run",
                data={"result_id": result.result_id, "request_id": request.request_id},
            )
        self.repository.save("progressive_model", updated.model_id, updated.revision_id, updated)
        self._record(
            event_type="ProgressiveDesignModelRevisionCreated",
            aggregate_id=updated.model_id,
            revision_id=updated.revision_id,
            actor=actor,
            reason="design-tool result confirmed" if confirmed else "design-tool draft recorded",
            data={"provider_result_id": result.result_id, "confirmed": str(confirmed).lower()},
        )
        return updated

    def confirm_design_tool_run(
        self,
        run: DesignToolRun,
        model: "ProgressiveDesignModel",
        *,
        actor: str = "human",
    ) -> "ProgressiveDesignModel":
        """Promote an already-recorded provider draft in a new run revision.

        ``design-attach`` creates a request/result pair in one command.  A
        later review of that exact pair must not regenerate a request (and
        therefore must not receive a new request ID) or overwrite the pending
        history.  This command keeps the original pending run immutable and
        records a ``.r2`` confirmed revision pointing at the newly projected
        model revision.
        """

        if run.confirmation != "pending":
            raise DomainStateError("design-tool run has already been confirmed")
        if run.candidate_revision_id != model.candidate_revision_id:
            raise DomainStateError("design-tool run and model reference different candidate revisions")
        if run.resulting_model_revision_id and run.resulting_model_revision_id != model.revision_id:
            parent_model = self.repository.get_revision("progressive_model", run.resulting_model_revision_id)
            if parent_model is None or parent_model.model_id != model.model_id or parent_model.revision_id != model.meta.parent_revision_id:
                raise DomainStateError("design-tool run does not belong to the current model revision")
        request = DesignToolRequest.model_validate(run.request_json)
        result = DesignToolResult.model_validate(run.result_json)
        if result.request_id != request.request_id:
            raise DomainStateError("persisted design-tool run contains mismatched request/result IDs")
        if result.candidate_revision_id != model.candidate_revision_id:
            raise DomainStateError("persisted design-tool result is stale for the current candidate revision")

        # Reuse the normal projection boundary without creating a second run.
        updated = attach_design_tool_result(model, result, actor=actor, confirmed=True)
        self.repository.save("progressive_model", updated.model_id, updated.revision_id, updated)
        previous_runs = [item for item in self.repository.list_revisions("design_tool_run") if item.run_id == run.run_id]
        next_revision = max((item.meta.revision for item in previous_runs), default=run.meta.revision) + 1
        confirmed_run = run.model_copy(update={
            "revision_id": f"{run.run_id}.r{next_revision}",
            "meta": RevisionMeta(revision=next_revision, parent_revision_id=run.revision_id, created_by=actor, reason="human-confirmed provider draft"),
            "resulting_model_revision_id": updated.revision_id,
            "confirmation": "confirmed",
        })
        self.repository.save("design_tool_run", confirmed_run.run_id, confirmed_run.revision_id, confirmed_run)
        self._record(
            event_type="DesignToolRunConfirmed",
            aggregate_id=confirmed_run.run_id,
            revision_id=confirmed_run.revision_id,
            actor=actor,
            reason="human-confirmed existing provider draft",
            data={"result_id": result.result_id, "request_id": request.request_id},
        )
        self._record(
            event_type="ProgressiveDesignModelRevisionCreated",
            aggregate_id=updated.model_id,
            revision_id=updated.revision_id,
            actor=actor,
            reason="human-confirmed existing design-tool draft",
            data={"provider_result_id": result.result_id, "confirmed": "true"},
        )
        return updated

    # ----- prototype evidence workflow --------------------------------------
    def import_prototype_run(
        self,
        run: PrototypeRun,
        *,
        protocol: object | None = None,
        require_lineage: bool = False,
        actor: str = "system",
    ) -> PrototypeRun:
        """Persist a run import without inferring any evidence from it.

        A run is merely a provenance envelope.  Provider/design-derived files
        may be attached for comparison, but remain explicitly non-evidence.
        """
        if protocol is not None and getattr(protocol, "protocol_id", run.protocol_id) != run.protocol_id:
            raise DomainStateError("prototype run references a different protocol")
        if protocol is not None and getattr(protocol, "protocol_revision", run.protocol_revision) != run.protocol_revision:
            raise DomainStateError("prototype run protocol revision does not match preregistration")
        if not run.conditions:
            raise DomainStateError("prototype run must record at least one condition")
        if protocol is not None:
            snapshot = protocol.model_dump(mode="json") if hasattr(protocol, "model_dump") else None
            if snapshot is not None:
                run = run.model_copy(update={"protocol_snapshot": snapshot})
        candidate = self.repository.get_revision("candidate", run.candidate_revision_id)
        if candidate is None and require_lineage:
            raise DomainStateError("prototype run candidate revision is not available")
        if run.model_revision_id:
            model = self.repository.get_revision("progressive_model", run.model_revision_id)
            if model is not None and model.candidate_revision_id != run.candidate_revision_id:
                raise DomainStateError("prototype run model revision belongs to another candidate")
        if self.repository.get_revision("prototype_run", run.revision_id) is not None:
            raise DomainStateError("prototype run revision already imported")
        for asset in run.source_assets:
            existing_asset = self.repository.get_revision("prototype_asset", asset.asset_id)
            if existing_asset is not None and (existing_asset.sha256 != asset.sha256 or existing_asset.uri != asset.uri):
                raise DomainStateError("prototype asset ID already names a different file")
        self.repository.save("prototype_run", run.run_id, run.revision_id, run)
        self._record(event_type="PrototypeRunImported", aggregate_id=run.run_id, revision_id=run.revision_id, actor=actor, reason="prototype run provenance imported")
        for asset in run.source_assets:
            self.import_prototype_asset(asset, actor=actor)
        return run

    def import_prototype_asset(self, asset: PrototypeAsset, *, actor: str = "system") -> PrototypeAsset:
        """Persist an asset hash as provenance; this never creates evidence."""
        existing = self.repository.get_revision("prototype_asset", asset.asset_id)
        if existing is not None:
            if existing.sha256 != asset.sha256 or existing.uri != asset.uri:
                raise DomainStateError("prototype asset ID already names a different file")
            return existing
        if existing is None:
            self.repository.save("prototype_asset", asset.asset_id, asset.asset_id, asset)
            self._record(event_type="PrototypeAssetImported", aggregate_id=asset.asset_id, revision_id=asset.asset_id, actor=actor, reason="prototype asset provenance imported")
        return asset

    # ----- external asset / observation workflow ---------------------------
    def import_external_asset(self, asset: ExternalAsset, *, actor: str = "system") -> ExternalAsset:
        """Record an external file without deriving facts from its contents."""
        if asset.provider.lower() == "blender" and asset.provenance == "external":
            asset = asset.model_copy(update={"provenance": "blender_derived"})
        existing = self.repository.get_revision("external_asset", asset.revision_id)
        if existing is not None:
            if existing.sha256 != asset.sha256 or existing.uri != asset.uri:
                raise DomainStateError("external asset revision already names a different file")
            return existing
        self.repository.save("external_asset", asset.asset_id, asset.revision_id, asset)
        self._record(event_type="ExternalAssetImported", aggregate_id=asset.asset_id, revision_id=asset.revision_id, actor=actor, reason="external asset hash and provenance recorded")
        return asset

    def import_external_assets(self, assets: Iterable[ExternalAsset], *, actor: str = "system") -> tuple[ExternalAsset, ...]:
        return tuple(self.import_external_asset(asset, actor=actor) for asset in assets)

    def import_observation_draft(self, draft: ObservationDraft, *, actor: str = "system") -> ObservationDraft:
        """Persist an asset interpretation as pending; no candidate fact is changed."""
        candidate = self.repository.get_revision("candidate", draft.candidate_revision_id)
        if candidate is None:
            raise DomainStateError("observation draft references an unknown candidate revision")
        declared_fact_ids = {fact.fact_id for fact in candidate.declared_facts}
        if draft.source_fact_id not in declared_fact_ids:
            raise DomainStateError("observation draft must reference a declared candidate fact")
        assets = {asset.asset_id: asset for asset in self.repository.list_revisions("external_asset")}
        if not set(draft.asset_ids).issubset(assets):
            raise DomainStateError("observation draft references an unimported external asset")
        if any(assets[item].status != "imported" for item in draft.asset_ids):
            raise DomainStateError("observation draft references an unavailable external asset")
        if self.repository.get_revision("observation_draft", draft.revision_id) is not None:
            raise DomainStateError("observation draft revision already imported")
        self.repository.save("observation_draft", draft.draft_id, draft.revision_id, draft)
        self._record(event_type="ObservationDraftImported", aggregate_id=draft.draft_id, revision_id=draft.revision_id, actor=actor, reason="external asset observation draft imported")
        return draft

    def confirm_observation_draft(
        self,
        draft: ObservationDraft,
        *,
        actor: str = "human",
        confirmation: str = "accepted",
        value: str | None = None,
        reason: str = "external observation manually confirmed",
    ) -> ConfirmedObservation:
        """Convert a pending draft into a confirmed design observation only."""
        persisted = self.repository.get_revision("observation_draft", draft.revision_id)
        if persisted is None:
            raise DomainStateError("observation draft is not persisted")
        if persisted.confirmation != "pending":
            raise DomainStateError("observation draft has already been reviewed")
        if confirmation not in {"accepted", "modified"}:
            raise DomainStateError("only accepted or modified drafts can create a confirmed observation")
        assets = {asset.asset_id: asset for asset in self.repository.list_revisions("external_asset")}
        if not set(draft.asset_ids).issubset(assets):
            raise DomainStateError("observation draft references an unimported external asset")
        source_asset = next((assets[item] for item in draft.asset_ids if item in assets), None)
        if source_asset is None:
            raise DomainStateError("confirmed observation requires an external asset source")
        observation_id = draft.confirmed_observation_id or _id("asset-observation")
        observed_value = value if confirmation == "modified" and value is not None else draft.proposed_value
        observation = ConfirmedObservation(
            observation_id=observation_id,
            meta=RevisionMeta(revision=1, created_by=actor, reason=reason),
            source_fact_id=draft.source_fact_id,
            subject=draft.subject,
            predicate=draft.predicate,
            value=observed_value,
            source_locator=f"asset:{source_asset.asset_id}#sha256:{source_asset.sha256}",
            confirmation=confirmation,
            confirmed_by=actor,
            provenance="blender_derived" if source_asset.provenance in {"blender_derived", "design_derived"} else "external_asset",
            source_draft_id=draft.draft_id,
        )
        next_revision = persisted.meta.revision + 1
        updated = persisted.model_copy(update={
            "revision_id": f"{persisted.draft_id}.r{next_revision}",
            "meta": RevisionMeta(revision=next_revision, parent_revision_id=persisted.revision_id, created_by=actor, reason=reason),
            "confirmation": confirmation,
            "confirmed_observation_id": observation.observation_id,
        })
        self.repository.save("observation_draft", updated.draft_id, updated.revision_id, updated)
        self.repository.save("confirmed_observation", observation.observation_id, observation.observation_id, observation)
        self._record(event_type="ObservationDraftConfirmed", aggregate_id=draft.draft_id, revision_id=updated.revision_id, actor=actor, reason=reason, data={"observation_id": observation.observation_id, "provenance": observation.provenance})
        return observation

    def review_observation_draft(
        self,
        draft: ObservationDraft,
        *,
        actor: str = "human",
        decision: str = "accepted",
        value: str | None = None,
        reason: str = "external observation manually reviewed",
    ) -> ObservationDraft | ConfirmedObservation:
        """Record accept/modify/reject without losing the human decision."""
        if decision in {"accepted", "modified"}:
            return self.confirm_observation_draft(draft, actor=actor, confirmation=decision, value=value, reason=reason)
        if decision not in {"rejected", "not_observable"}:
            raise DomainStateError("observation review decision must be accepted, modified, rejected or not_observable")
        persisted = self.repository.get_revision("observation_draft", draft.revision_id)
        if persisted is None or persisted.confirmation != "pending":
            raise DomainStateError("observation draft is not pending")
        next_revision = persisted.meta.revision + 1
        updated = persisted.model_copy(update={
            "revision_id": f"{persisted.draft_id}.r{next_revision}",
            "meta": RevisionMeta(revision=next_revision, parent_revision_id=persisted.revision_id, created_by=actor, reason=reason),
            "confirmation": "rejected",
            "observable_status": "not_observable" if decision == "not_observable" else persisted.observable_status,
        })
        self.repository.save("observation_draft", updated.draft_id, updated.revision_id, updated)
        self._record(event_type="ObservationDraftRejected" if decision == "rejected" else "ObservationDraftNotObservable", aggregate_id=draft.draft_id, revision_id=updated.revision_id, actor=actor, reason=reason)
        return updated

    def confirmed_observations_for_candidate(self, candidate_revision_id: str) -> tuple[ConfirmedObservation, ...]:
        """Return latest asset-backed confirmations for a candidate revision."""
        candidate = self.repository.get_revision("candidate", candidate_revision_id)
        if candidate is None:
            raise DomainStateError("candidate revision is not available")
        fact_ids = {fact.fact_id for fact in candidate.declared_facts}
        latest: dict[str, ConfirmedObservation] = {}
        for item in self.repository.list_revisions("confirmed_observation"):
            if item.source_fact_id in fact_ids:
                previous = latest.get(item.observation_id)
                if previous is None or item.meta.revision > previous.meta.revision:
                    latest[item.observation_id] = item
        return tuple(latest.values())

    def freeze_facts_from_asset_observations(
        self,
        candidate: DesignCandidate,
        observation_ids: Iterable[str],
        *,
        actor: str = "human",
    ) -> CandidateFactsSnapshot:
        selected = set(observation_ids)
        observations = tuple(item for item in self.confirmed_observations_for_candidate(candidate.candidate_revision_id) if item.observation_id in selected)
        if len(observations) != len(selected):
            raise DomainStateError("facts freeze references unknown asset-backed observations")
        return self.freeze_facts(candidate, actor=actor, confirmed_observations=observations)

    create_observation_draft = import_observation_draft

    def import_measurement_observation(
        self,
        observation: MeasurementObservation,
        *,
        run: PrototypeRun | None = None,
        actor: str = "system",
    ) -> MeasurementObservation:
        """Import one raw observation as a draft, retaining missing/failed data."""
        persisted_run = self.repository.get_current("prototype_run", observation.run_id)
        if persisted_run is None or persisted_run.run_id != observation.run_id:
            raise DomainStateError("measurement observation references an unknown prototype run")
        if run is not None and run.revision_id != persisted_run.revision_id:
            raise DomainStateError("measurement observation references a stale prototype run revision")
        if observation.condition not in persisted_run.conditions:
            raise DomainStateError("measurement observation condition is not registered on the prototype run")
        registered_measures = {
            str(item.get("measure_id"))
            for item in persisted_run.protocol_snapshot.get("measures", [])
            if isinstance(item, dict) and item.get("measure_id")
        }
        if registered_measures and observation.measure_id not in registered_measures:
            raise DomainStateError("measurement observation measure is not registered in the protocol snapshot")
        asset_ids = {asset.asset_id for asset in persisted_run.source_assets}
        if not set(observation.source_asset_ids).issubset(asset_ids):
            raise DomainStateError("observation references an asset outside its prototype run")
        derived_asset_ids = {
            asset.asset_id for asset in persisted_run.source_assets
            if asset.provenance in {"blender_derived", "design_derived"} or asset.provider.lower() == "blender"
        }
        if derived_asset_ids.intersection(observation.source_asset_ids):
            # Provenance is determined by the imported asset chain, never by
            # a caller-provided evidence label.
            observation = observation.model_copy(update={"provenance": "blender_derived"})
        if observation.status != "draft":
            # Imports are never allowed to smuggle in a human decision.
            observation = observation.model_copy(update={"status": "draft", "reviewer": None, "reviewed_at": None})
        if self.repository.get_revision("measurement_observation", observation.revision_id) is not None:
            raise DomainStateError("measurement observation revision already imported")
        self.repository.save("measurement_observation", observation.observation_id, observation.revision_id, observation)
        self._record(event_type="MeasurementObservationImported", aggregate_id=observation.observation_id, revision_id=observation.revision_id, actor=actor, reason="measurement observation draft imported")
        return observation

    # Compatibility plural command for batch/file import clients.
    def import_measurement_observations(self, run: PrototypeRun, observations: Iterable[MeasurementObservation], *, actor: str = "system") -> tuple[MeasurementObservation, ...]:
        if self.repository.get_revision("prototype_run", run.revision_id) is None:
            self.import_prototype_run(run, actor=actor)
        return tuple(self.import_measurement_observation(item, run=run, actor=actor) for item in observations)

    def review_evidence(
        self,
        run: PrototypeRun,
        observations: Iterable[MeasurementObservation] | None = None,
        *,
        decision: str,
        reviewer: str = "human",
        evidence_level_after: str = "none",
        confirmed_observation_ids: Iterable[str] = (),
        rationale: str = "human evidence review",
        limitations: Iterable[str] = (),
        actor: str | None = None,
    ) -> EvidenceReview:
        """Record the human gate that may promote observations to evidence."""
        persisted_run = self.repository.get_revision("prototype_run", run.revision_id)
        if persisted_run is None or persisted_run.run_id != run.run_id:
            raise DomainStateError("evidence review references an unknown prototype run")
        stored = {item.observation_id: item for item in self.repository.list_revisions("measurement_observation") if item.run_id == run.run_id}
        if observations is not None:
            for item in observations:
                persisted = stored.get(item.observation_id)
                if persisted is None or persisted.revision_id != item.revision_id:
                    raise DomainStateError("evidence review can only review persisted observations")
        ids = tuple(confirmed_observation_ids)
        if not set(ids).issubset(stored):
            raise DomainStateError("evidence review references unknown observations")
        # Derived Blender/design material can be reviewed as a limitation but
        # is never eligible for a confirmed evidence set.
        eligible = tuple(item_id for item_id in ids if stored[item_id].provenance not in {"blender_derived", "design_derived"})
        if decision == "confirmed":
            decision = "accepted"
        if decision in {"accepted", "modified"} and set(eligible) != set(ids):
            raise DomainStateError("Blender/design-derived observations cannot be promoted to prototype evidence")
        if decision in {"accepted", "modified"}:
            for item_id in eligible:
                item = stored[item_id]
                if item.status != "draft" or item.missing_reason is not None or item.value is None:
                    raise DomainStateError("only measured draft observations with values can be confirmed")
                next_rev = item.meta.revision + 1
                confirmed = item.model_copy(update={"revision_id": f"{item.observation_id}.r{next_rev}", "meta": RevisionMeta(revision=next_rev, parent_revision_id=item.revision_id, created_by=reviewer, reason="human evidence review"), "status": "confirmed", "reviewer": reviewer, "reviewed_at": datetime.now(timezone.utc)})
                self.repository.save("measurement_observation", confirmed.observation_id, confirmed.revision_id, confirmed)
        level_order = {"none": 0, "exploratory": 1, "observed": 2, "supported": 3, "replicated": 4}
        previous_levels = [
            item.evidence_level_after
            for item in self.repository.list_revisions("evidence_review")
            if item.run_id == run.run_id
        ]
        before_level = max(previous_levels, key=lambda value: level_order.get(value, 0), default="none")
        review_id = _id("evidence-review")
        review = EvidenceReview(
            review_id=review_id,
            revision_id=f"{review_id}.r1",
            meta=RevisionMeta(revision=1, created_by=reviewer, reason=rationale),
            run_id=run.run_id,
            observation_ids=tuple(stored),
            reviewer=reviewer,
            decision=decision,
            evidence_level_before=before_level,
            evidence_level_after=evidence_level_after if decision in {"accepted", "modified"} else "none",
            confirmed_observation_ids=eligible,
            rationale=rationale,
            limitations=tuple(limitations),
        )
        self.repository.save("evidence_review", review.review_id, review.revision_id, review)
        if review.evidence_level_after != "none" and run.model_revision_id:
            model = self.repository.get_revision("progressive_model", run.model_revision_id)
            if model is not None:
                layers = list(model.layers)
                for index, layer in enumerate(layers):
                    if layer.layer == "prototype_evidence":
                        layers[index] = layer.model_copy(update={"status": "partial", "artifact_refs": tuple(dict.fromkeys(layer.artifact_refs + (review.review_id,))), "gaps": tuple(g for g in layer.gaps if g != "awaiting human evidence review")})
                        break
                else:
                    from psyteardown.experience.models import ModelLayerStatus
                    layers.append(ModelLayerStatus(layer="prototype_evidence", status="partial", artifact_refs=(review.review_id,)))
                next_revision = max((item.meta.revision for item in self.repository.list_revisions("progressive_model") if item.model_id == model.model_id), default=model.meta.revision) + 1
                updated_model = model.model_copy(update={"revision_id": f"{model.model_id}.r{next_revision}", "meta": RevisionMeta(revision=next_revision, parent_revision_id=model.revision_id, created_by=reviewer, reason="human evidence review projected"), "layers": tuple(layers), "provider_result_ids": model.provider_result_ids})
                self.repository.save("progressive_model", updated_model.model_id, updated_model.revision_id, updated_model)
                self._record(event_type="PrototypeEvidenceProjected", aggregate_id=updated_model.model_id, revision_id=updated_model.revision_id, actor=reviewer, reason="human-confirmed evidence projected to model")
        self._record(event_type="EvidenceReviewRecorded", aggregate_id=review.review_id, revision_id=review.revision_id, actor=actor or reviewer, reason=rationale, data={"run_id": run.run_id, "decision": decision, "evidence_level": review.evidence_level_after})
        return review

    def confirm_measurement_observations(self, run: PrototypeRun, observation_ids: Iterable[str], *, reviewer: str = "human", evidence_level: str = "observed", rationale: str = "human confirmed measurements") -> EvidenceReview:
        return self.review_evidence(run, decision="accepted", reviewer=reviewer, evidence_level_after=evidence_level, confirmed_observation_ids=observation_ids, rationale=rationale)

    def compile_scenario_policy(self, scenario: FutureMovementScenario, *, actor: str = "system", freeze: bool = False) -> ScenarioPolicy:
        policy = build_scenario_policy(scenario, actor=actor, status="frozen" if freeze else "candidate")
        existing = self.repository.get_revision("scenario_policy", policy.revision_id)
        if existing is not None:
            return existing
        self.repository.save("scenario_policy", policy.policy_id, policy.revision_id, policy)
        self._record(event_type="ScenarioPolicyCompiled", aggregate_id=policy.policy_id, revision_id=policy.revision_id, actor=actor, reason="deterministic scenario policy compiled")
        return policy

    def compile_scenario_policies(self, scenarios: Iterable[FutureMovementScenario], *, actor: str = "system", freeze: bool = False) -> tuple[ScenarioPolicy, ...]:
        return tuple(self.compile_scenario_policy(scenario, actor=actor, freeze=freeze) for scenario in scenarios)

    record_measurement_observation = import_measurement_observation
    create_evidence_review = review_evidence
    confirm_evidence_review = review_evidence

    # ----- event/audit helpers -------------------------------------------------
    def _record(self, *, event_type: str, aggregate_id: str, revision_id: str, actor: str, reason: str, data: dict[str, str] | None = None) -> None:
        self.repository.emit_domain(
            DomainEvent(
                event_id=_id("domain"),
                event_type=event_type,
                aggregate_id=aggregate_id,
                aggregate_revision_id=revision_id,
                data=tuple(sorted((data or {}).items())),
            )
        )
        self.repository.record_audit(
            AuditEvent(
                audit_id=_id("audit"),
                action=event_type,
                target_id=aggregate_id,
                target_revision_id=revision_id,
                actor=actor,
                reason=reason,
            )
        )

    def _save_iteration(self, iteration: DesignIteration, *, actor: str, reason: str) -> DesignIteration:
        self.repository.save("iteration", iteration.iteration_id, iteration.revision_id, iteration)
        self._record(event_type="DesignIterationChanged", aggregate_id=iteration.iteration_id, revision_id=iteration.revision_id, actor=actor, reason=reason)
        return iteration

    def _advance_iteration(self, iteration: DesignIteration, *, actor: str, reason: str, **changes) -> DesignIteration:
        next_revision = iteration.meta.revision + 1
        next_id = _id(f"{iteration.iteration_id}.r{next_revision}")
        updated = iteration.model_copy(
            update={
                **changes,
                "revision_id": next_id,
                "meta": RevisionMeta(revision=next_revision, parent_revision_id=iteration.revision_id, created_by=actor, reason=reason),
            }
        )
        return self._save_iteration(updated, actor=actor, reason=reason)

    def _current_iteration(self, iteration: DesignIteration) -> DesignIteration:
        current = self.repository.get_current("iteration", iteration.iteration_id)
        return current or iteration

    # ----- brief and iteration -------------------------------------------------
    def freeze_brief(self, brief: DesignBrief, *, actor: str = "human", reason: str = "brief approved") -> DesignBrief:
        validate_brief_for_freeze(brief)
        if brief.status == "frozen":
            return brief
        frozen = brief.model_copy(update={"status": "frozen"})
        self.repository.save("brief", frozen.brief_id, frozen.revision_id, frozen)
        self._record(event_type="BriefFrozen", aggregate_id=frozen.brief_id, revision_id=frozen.revision_id, actor=actor, reason=reason)
        return frozen

    def create_iteration(self, brief: DesignBrief, *, round_number: int = 1, actor: str = "system", parent_iteration_id: str | None = None) -> DesignIteration:
        if brief.status != "frozen":
            raise DomainStateError("brief must be frozen before creating an iteration")
        if round_number not in (1, 2):
            raise DomainStateError("first slice supports exactly two rounds")
        iteration_id = _id(f"iteration-r{round_number}")
        iteration = DesignIteration(
            iteration_id=iteration_id,
            revision_id=f"{iteration_id}.r1",
            meta=RevisionMeta(revision=1, created_by=actor, reason="iteration created"),
            brief_revision_id=brief.revision_id,
            round_number=round_number,
            parent_iteration_id=parent_iteration_id,
        )
        self._save_iteration(iteration, actor=actor, reason="iteration created")
        return iteration

    # ----- candidate import and facts freeze ----------------------------------
    def import_candidates(self, iteration: DesignIteration, *, actor: str = "system") -> tuple[DesignCandidate, ...]:
        iteration = self._current_iteration(iteration)
        if iteration.status != "created":
            raise DomainStateError("candidates can only be imported into a new iteration")
        brief = self.repository.get_revision("brief", iteration.brief_revision_id)
        if brief is None:
            raise DomainStateError("iteration brief snapshot is not available")
        expected = brief.round_one_size if iteration.round_number == 1 else brief.round_two_variants_per_direction
        if self.design_generator is None:
            raise DomainStateError("design generator is not configured")
        drafts = self.design_generator.generate(brief, round_number=iteration.round_number, count=expected)
        if len(drafts) != expected:
            raise DomainStateError(f"round {iteration.round_number} requires {expected} candidates")
        candidates: list[DesignCandidate] = []
        for draft in drafts:
            candidate = build_candidate(draft, brief, actor=actor, reason="candidate imported")
            self.repository.save("candidate", candidate.candidate_id, candidate.candidate_revision_id, candidate)
            self._record(event_type="CandidateImported", aggregate_id=candidate.candidate_id, revision_id=candidate.candidate_revision_id, actor=actor, reason="candidate imported")
            candidates.append(candidate)
        gaps = check_batch_divergence(candidates, brief)
        next_status = IterationStatus.CANDIDATES_IMPORTED
        updated = self._advance_iteration(iteration, actor=actor, reason="candidates imported", status=next_status, candidate_revision_ids=tuple(c.candidate_revision_id for c in candidates), divergence_gaps=gaps)
        if gaps:
            self._record(event_type="DivergenceGapDetected", aggregate_id=updated.iteration_id, revision_id=updated.revision_id, actor=actor, reason=";".join(gaps))
        return tuple(candidates)

    def freeze_facts(self, candidate: DesignCandidate, *, actor: str = "human", confirmed_observations: tuple | None = None) -> CandidateFactsSnapshot:
        if confirmed_observations is None and any(
            fact.risk_relevance != "ordinary" for fact in candidate.declared_facts
        ):
            raise DomainStateError("privacy, safety and control facts require item-level confirmation")
        evidence_review_ids: set[str] = set()
        extra_dependencies: list[DependencyRef] = []
        if confirmed_observations:
            for observation in confirmed_observations:
                if observation.source_fact_id not in {fact.fact_id for fact in candidate.declared_facts}:
                    raise DomainStateError("confirmed observation references a fact outside candidate revision")
                if observation.provenance == "blender_derived":
                    raise DomainStateError("Blender-derived observations cannot be frozen as candidate facts")
                extra_dependencies.append(DependencyRef(object_type="confirmed_observation", object_id=observation.observation_id, revision=observation.meta.revision))
                if observation.source_draft_id:
                    draft = self.repository.get_current("observation_draft", observation.source_draft_id)
                    if draft is None or draft.confirmed_observation_id != observation.observation_id:
                        raise DomainStateError("confirmed observation source draft is not persisted or does not match")
                    extra_dependencies.append(DependencyRef(object_type="observation_draft", object_id=draft.draft_id, revision=draft.meta.revision))
                    for asset_id in draft.asset_ids:
                        asset = next((item for item in self.repository.list_revisions("external_asset") if item.asset_id == asset_id), None)
                        if asset is None:
                            raise DomainStateError("confirmed observation source asset is not persisted")
                        extra_dependencies.append(DependencyRef(object_type="external_asset", object_id=asset.asset_id, revision=asset.meta.revision))
                for review in self.repository.list_revisions("evidence_review"):
                    if observation.observation_id in review.confirmed_observation_ids and review.decision in {"accepted", "modified"}:
                        evidence_review_ids.add(review.review_id)
        facts = freeze_candidate_facts(
            candidate,
            actor=actor,
            confirmed_observations=confirmed_observations,
            dependencies=tuple(dict.fromkeys(extra_dependencies)),
            evidence_review_ids=tuple(sorted(evidence_review_ids)),
        )
        self.repository.save("facts", facts.facts_snapshot_id, facts.facts_snapshot_id, facts)
        self._record(event_type="CandidateFactsFrozen", aggregate_id=candidate.candidate_id, revision_id=facts.facts_snapshot_id, actor=actor, reason="facts confirmed")
        # Advance the owning iteration only when every imported candidate has a
        # frozen fact snapshot; a single frozen candidate is not enough to run
        # a fair cross-candidate comparison.
        iterations = self.repository.list_revisions("iteration")
        for iteration in reversed(iterations):
            if candidate.candidate_revision_id not in iteration.candidate_revision_ids:
                continue
            frozen_ids = {
                item.candidate_revision_id
                for item in self.repository.list_revisions("facts")
                if item.candidate_revision_id in iteration.candidate_revision_ids
            }
            if set(iteration.candidate_revision_ids).issubset(frozen_ids) and iteration.status == "candidates_imported":
                self._advance_iteration(iteration, actor=actor, reason="all candidate facts frozen", status=IterationStatus.FACTS_FROZEN, facts_snapshot_ids=tuple(frozen_ids))
            break
        return facts

    # ----- review draft, claim judge and confirmation -------------------------
    def generate_review_drafts(self, facts: CandidateFactsSnapshot) -> tuple[ReviewItemDraft, ...]:
        if self.review_reasoner is None:
            raise DomainStateError("review reasoner is not configured")
        brief = self.repository.get_revision("brief", facts.brief_revision_id)
        if brief is None:
            raise DomainStateError("brief snapshot is not available")
        return tuple(self.review_reasoner.generate(brief, facts))

    def judge_review_draft(self, facts: CandidateFactsSnapshot, draft: ReviewItemDraft) -> ClaimJudgement:
        if self.claim_judge is None:
            raise DomainStateError("claim judge is not configured")
        brief = self.repository.get_revision("brief", facts.brief_revision_id)
        if brief is None:
            raise DomainStateError("brief snapshot is not available")
        return self.claim_judge.judge(brief, facts, draft)

    def confirm_review_item(self, facts: CandidateFactsSnapshot, draft: ReviewItemDraft, judgement: ClaimJudgement, *, actor: str = "human", reason: str = "review item confirmed") -> ReviewItem:
        if judgement.review_item_id != draft.review_item_id:
            raise DomainStateError("claim judgement does not match review draft")
        if not set(draft.fact_ids).issubset({o.source_fact_id for o in facts.observations}):
            raise DomainStateError("review item references facts outside frozen snapshot")
        if draft.event_id not in {event.event_id for event in facts.events}:
            raise DomainStateError("review item references an event outside frozen snapshot")
        brief = self.repository.get_revision("brief", facts.brief_revision_id)
        if brief is None:
            raise DomainStateError("brief snapshot is not available")
        if not set(draft.criterion_ids).issubset({criterion.criterion_id for criterion in brief.criteria}):
            raise DomainStateError("review item references a criterion outside frozen brief")
        approved_rules = {
            item.approved_rule_id
            for item in brief.prohibited_experiences
            if item.severity == "hard" and item.approved_rule_id
        }
        if draft.status == "blocked" and not set(draft.approved_rule_ids).issubset(approved_rules):
            raise DomainStateError("only a frozen brief's approved hard-risk rules can block")
        patches: list[VariablePatch] = []
        for patch_draft in draft.actionable_changes:
            patch_revision = _id(f"{patch_draft.patch_id}.r1")
            patches.append(
                VariablePatch(
                    patch_id=patch_draft.patch_id,
                    revision_id=patch_revision,
                    meta=RevisionMeta(revision=1, created_by=actor, reason="actionable change confirmed"),
                    review_item_revision_id=f"{draft.review_item_id}.r1",
                    variable_id=patch_draft.variable_id,
                    operation=patch_draft.operation,
                    from_value=patch_draft.from_value,
                    to_value=patch_draft.to_value,
                    scope=patch_draft.scope,
                    enforcement=patch_draft.suggested_enforcement,
                    rationale=patch_draft.rationale,
                    evidence_refs=tuple(patch_draft.evidence_refs),
                    expected_effect=patch_draft.expected_effect,
                    risks=tuple(patch_draft.risks),
                    verification=patch_draft.verification,
                )
            )
        revision_id = f"{draft.review_item_id}.r1"
        item = ReviewItem(
            review_item_id=draft.review_item_id,
            review_item_revision_id=revision_id,
            meta=RevisionMeta(revision=1, created_by=actor, reason=reason),
            candidate_id=facts.candidate_id,
            candidate_revision_id=facts.candidate_revision_id,
            facts_snapshot_id=facts.facts_snapshot_id,
            brief_revision_id=facts.brief_revision_id,
            event_id=draft.event_id,
            criterion_ids=tuple(draft.criterion_ids),
            fact_ids=tuple(draft.fact_ids),
            context=draft.context,
            observation=draft.observation,
            hypothesis=draft.hypothesis,
            alternative_explanations=tuple(draft.alternative_explanations),
            evidence=tuple(draft.evidence),
            alignment=draft.proposed_alignment,
            status=draft.status,
            risk=draft.risk,
            tradeoff=draft.tradeoff,
            variable_patches=tuple(patches),
            approved_rule_ids=tuple(draft.approved_rule_ids),
            unblock_condition=draft.unblock_condition,
            validation_task=draft.validation_task,
            claim_judgement=judgement,
        )
        self.repository.save("review", item.review_item_id, item.review_item_revision_id, item)
        self._record(event_type="ReviewItemConfirmed", aggregate_id=item.review_item_id, revision_id=item.review_item_revision_id, actor=actor, reason=reason)
        return item

    def compare_candidates(self, iteration: DesignIteration, *, actor: str = "system") -> CandidatePartialOrder:
        iteration = self._current_iteration(iteration)
        if iteration.status != "facts_frozen":
            raise DomainStateError("all candidate facts must be frozen before comparison")
        if iteration.divergence_gaps:
            raise DomainStateError("candidate batch has unresolved divergence gaps")
        brief = self.repository.get_revision("brief", iteration.brief_revision_id)
        if brief is None:
            raise DomainStateError("brief snapshot is not available")
        candidates = [self.repository.get_revision("candidate", rid) for rid in iteration.candidate_revision_ids]
        facts_list = [self._facts_for_candidate(candidate) for candidate in candidates if candidate is not None]
        evaluations = []
        review_ids: list[str] = []
        facts_ids: list[str] = []
        for facts in facts_list:
            reviews = tuple(self._reviews_for_candidate(facts.candidate_id, facts.candidate_revision_id))
            if not reviews:
                raise DomainStateError(f"candidate {facts.candidate_id} has no confirmed ReviewItems")
            evaluation = aggregate_evaluation(brief, facts, reviews)
            self.repository.save("evaluation", evaluation.evaluation_id, evaluation.evaluation_id, evaluation)
            evaluations.append(evaluation)
            facts_ids.append(facts.facts_snapshot_id)
            review_ids.extend(item.review_item_revision_id for item in reviews)
        order = build_partial_order(brief, iteration, tuple(evaluations))
        self.repository.save("partial_order", order.partial_order_id, order.partial_order_id, order)
        updated = self._advance_iteration(iteration, actor=actor, reason="candidate comparison", status=IterationStatus.COMPARED, facts_snapshot_ids=tuple(facts_ids), review_item_revision_ids=tuple(review_ids), evaluation_ids=tuple(e.evaluation_id for e in evaluations), partial_order_id=order.partial_order_id)
        self._record(event_type="CandidateCompared", aggregate_id=updated.iteration_id, revision_id=updated.revision_id, actor=actor, reason="deterministic partial order")
        return order

    # ----- selection, prompt and second round ---------------------------------
    def select_candidates(self, iteration: DesignIteration, order: CandidatePartialOrder, *, candidate_ids: Iterable[str], action: str = "select", rationale: str = "human selection", actor: str = "human", required_followups: Iterable[str] = ()) -> SelectionDecision:
        iteration = self._current_iteration(iteration)
        if iteration.status != "compared":
            raise DomainStateError("candidate selection requires a completed comparison")
        selected = tuple(candidate_ids)
        if not selected:
            raise DomainStateError("selection requires at least one candidate")
        if len(selected) > 2:
            raise DomainStateError("at most two preferred branches may proceed")
        if any(candidate_id in order.blocked for candidate_id in selected):
            raise DomainStateError("blocked candidates cannot be selected")
        if action == "select" and any(candidate_id in order.needs_evidence for candidate_id in selected):
            raise DomainStateError("needs_evidence can only proceed with explore_further")
        decision = SelectionDecision(
            decision_id=_id("selection"),
            revision_id=_id("selection.r1"),
            meta=RevisionMeta(revision=1, created_by=actor, reason=rationale),
            iteration_id=iteration.iteration_id,
            partial_order_id=order.partial_order_id,
            action=action,
            candidate_ids=selected,
            decision_basis=tuple(f"tier:{next((r.tier.value for r in order.reasons if r.candidate_id == c), 'unknown')}" for c in selected),
            overridden_tier=("needs_evidence" if action == "explore_further" else None),
            required_followups=tuple(required_followups),
            rationale=rationale,
        )
        self.repository.save("selection", decision.decision_id, decision.revision_id, decision)
        updated = self._advance_iteration(iteration, actor=actor, reason="selection confirmed", status=IterationStatus.SELECTED, selection_decision_id=decision.revision_id)
        self._record(event_type="CandidateSelected", aggregate_id=updated.iteration_id, revision_id=updated.revision_id, actor=actor, reason=rationale)
        return decision

    def confirm_next_prompt(self, iteration: DesignIteration, decision: SelectionDecision, *, actor: str = "human", validation_task_ids: Iterable[str] = ()) -> NextDesignPrompt:
        iteration = self._current_iteration(iteration)
        if iteration.status != "selected":
            raise DomainStateError("next prompt requires a confirmed selection")
        if decision.iteration_id != iteration.iteration_id:
            raise DomainStateError("selection belongs to another iteration")
        candidates = [self.repository.get_revision("candidate", rid) for rid in iteration.candidate_revision_ids]
        selected_revision_ids = tuple(c.candidate_revision_id for c in candidates if c and c.candidate_id in decision.candidate_ids)
        if len(selected_revision_ids) != len(decision.candidate_ids):
            raise DomainStateError("selection references a candidate outside the iteration")
        validation_task_ids = tuple(validation_task_ids)
        if decision.action == "explore_further" and not validation_task_ids:
            raise DomainStateError("explore_further selection requires a validation task")
        patches = [patch for candidate_id in decision.candidate_ids for item in self._reviews_for_candidate(candidate_id, None) for patch in item.variable_patches]
        conflicts = find_patch_conflicts(patches)
        if conflicts:
            raise DomainStateError("unresolved VariablePatch conflicts: " + ", ".join(f"{left}/{right}" for left, right in conflicts))
        if not patches and decision.action != "explore_further":
            raise DomainStateError("next prompt requires at least one confirmed VariablePatch")
        prompt = NextDesignPrompt(
            prompt_id=_id("next-prompt"),
            revision_id=_id("next-prompt.r1"),
            meta=RevisionMeta(revision=1, created_by=actor, reason="next design prompt confirmed"),
            brief_revision_id=iteration.brief_revision_id,
            iteration_id=iteration.iteration_id,
            selected_candidate_revision_ids=selected_revision_ids,
            confirmed_patch_revision_ids=tuple(p.revision_id for p in patches),
            validation_task_ids=validation_task_ids,
        )
        self.repository.save("prompt", prompt.prompt_id, prompt.revision_id, prompt)
        updated = self._advance_iteration(iteration, actor=actor, reason="next prompt confirmed", status=IterationStatus.PROMPT_CONFIRMED, next_prompt_id=prompt.revision_id)
        self._record(event_type="NextPromptConfirmed", aggregate_id=updated.iteration_id, revision_id=updated.revision_id, actor=actor, reason="human confirmed next prompt")
        return prompt

    def generate_second_round(self, iteration: DesignIteration, prompt: NextDesignPrompt, *, actor: str = "system") -> tuple[DesignIteration, tuple[DesignCandidate, ...]]:
        iteration = self._current_iteration(iteration)
        if iteration.round_number != 1 or iteration.status != "prompt_confirmed":
            raise DomainStateError("second round requires a prompt-confirmed first iteration")
        brief = self.repository.get_revision("brief", iteration.brief_revision_id)
        if brief is None or self.design_generator is None:
            raise DomainStateError("brief or design generator is not configured")
        requested = len(prompt.selected_candidate_revision_ids) * brief.round_two_variants_per_direction
        drafts = self.design_generator.generate(brief, round_number=2, count=requested, prompt=prompt)
        if len(drafts) != requested:
            raise DomainStateError(f"second round requires {requested} variants")
        candidates: list[DesignCandidate] = []
        parent_ids = set(prompt.selected_candidate_revision_ids)
        for draft in drafts:
            if draft.parent_candidate_revision_id not in parent_ids:
                raise DomainStateError("second-round candidate must name a selected parent revision")
            candidate = build_candidate(draft, brief, actor=actor, reason="second-round candidate imported")
            self.repository.save("candidate", candidate.candidate_id, candidate.candidate_revision_id, candidate)
            self._record(event_type="CandidateImported", aggregate_id=candidate.candidate_id, revision_id=candidate.candidate_revision_id, actor=actor, reason="second-round candidate imported")
            candidates.append(candidate)
        counts_by_parent = {
            parent_id: sum(
                candidate.parent_candidate_revision_id == parent_id
                for candidate in candidates
            )
            for parent_id in parent_ids
        }
        if any(count != brief.round_two_variants_per_direction for count in counts_by_parent.values()):
            raise DomainStateError("each selected direction requires exactly three variants")
        second = self.create_iteration(
            brief,
            round_number=2,
            actor=actor,
            parent_iteration_id=iteration.iteration_id,
        )
        second = self._advance_iteration(
            second,
            actor=actor,
            reason="second-round candidates imported",
            status=IterationStatus.CANDIDATES_IMPORTED,
            candidate_revision_ids=tuple(c.candidate_revision_id for c in candidates),
            divergence_gaps=check_batch_divergence(candidates, brief),
        )
        return second, tuple(candidates)

    # ----- cross-round repair trace -------------------------------------------
    def build_variable_repair_trace(self, parent: DesignCandidate, child: DesignCandidate, patches: tuple[VariablePatch, ...], *, actor: str = "system", issue_improvements: tuple[IssueImprovement, ...] | None = None) -> VariableRepairTrace:
        if child.parent_candidate_revision_id != parent.candidate_revision_id:
            raise DomainStateError("child candidate does not point at parent revision")
        parent_values = {value.variable_id: value for value in parent.variables}
        child_values = {value.variable_id: value for value in child.variables}
        declarations = dict(child.generator_application_declarations)
        applications: list[PatchApplicationTrace] = []
        for patch in patches:
            actual = child_values.get(patch.variable_id)
            expected = patch.to_value
            if actual is None or actual.missing_reason is not None:
                adoption = "unverifiable"
                reason = "child fact is missing or not observable"
            elif expected is not None and actual.normalized_value == expected.normalized_value:
                adoption = "adopted"
                reason = "confirmed child variable matches patch target"
            elif actual.normalized_value != parent_values.get(patch.variable_id, actual).normalized_value:
                adoption = "partially_adopted"
                reason = "child variable changed but does not fully match target"
            else:
                adoption = "not_adopted"
                reason = "confirmed child variable did not change"
            applications.append(PatchApplicationTrace(patch_revision_id=patch.revision_id, variable_id=patch.variable_id, from_value=parent_values.get(patch.variable_id), expected_value=expected, actual_value=actual, adoption=adoption, generator_declaration=declarations.get(patch.patch_id), reason=reason))
        if issue_improvements is None:
            source_review_ids = tuple(dict.fromkeys(patch.review_item_revision_id for patch in patches))
            issue_improvements = tuple(
                IssueImprovement(
                    review_item_revision_id=review_id,
                    status="indeterminate",
                    evidence_refs=(child.candidate_revision_id,),
                    reason="no confirmed cross-round issue assessment was supplied",
                )
                for review_id in source_review_ids
            )
        elif not {item.review_item_revision_id for item in issue_improvements}.issubset(
            {patch.review_item_revision_id for patch in patches}
        ):
            raise DomainStateError("issue improvement must reference a patched ReviewItem")
        trace = VariableRepairTrace(
            trace_id=_id("repair-trace"),
            meta=RevisionMeta(revision=1, created_by=actor, reason="fact-based patch adoption"),
            parent_candidate_revision_id=parent.candidate_revision_id,
            child_candidate_revision_id=child.candidate_revision_id,
            brief_revision_id=parent.brief_revision_id,
            patch_applications=tuple(applications),
            issue_improvements=issue_improvements,
        )
        self.repository.save("repair_trace", trace.trace_id, trace.trace_id, trace)
        self._record(event_type="VariableRepairTracked", aggregate_id=trace.trace_id, revision_id=trace.trace_id, actor=actor, reason="fact-based patch adoption")
        return trace

    def _facts_for_candidate(self, candidate: DesignCandidate | None) -> CandidateFactsSnapshot:
        if candidate is None:
            raise DomainStateError("candidate revision is not available")
        facts = [f for f in self.repository.list_revisions("facts") if getattr(f, "candidate_revision_id", None) == candidate.candidate_revision_id]
        if not facts:
            raise DomainStateError(f"candidate {candidate.candidate_id} has no frozen facts")
        return facts[-1]

    def _reviews_for_candidate(self, candidate_id: str, candidate_revision_id: str | None) -> list[ReviewItem]:
        return [item for item in self.repository.list_revisions("review") if item.candidate_id == candidate_id and (candidate_revision_id is None or item.candidate_revision_id == candidate_revision_id)]
