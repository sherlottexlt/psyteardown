"""Provider protocols and deterministic fake adapters for the first slice."""

from __future__ import annotations

from typing import Protocol

from psyteardown.experience.models import (
    CandidateDraft,
    ClaimJudgement,
    CandidateFactsSnapshot,
    DesignBrief,
    DesignComponent,
    DesignShape,
    DesignSpecification,
    DeclaredFact,
    DesignVariableValue,
    EventStep,
    InterventionEventSequence,
    ResponseBranch,
    ReviewItemDraft,
)


class ExperienceProviderError(RuntimeError):
    """A fake/provider queue was exhausted or returned an invalid item."""


class DesignGenerator(Protocol):
    def generate(
        self,
        brief: DesignBrief,
        *,
        round_number: int = 1,
        count: int | None = None,
        n: int | None = None,
        prompt: object | None = None,
    ) -> list[CandidateDraft]: ...


class ReviewReasoner(Protocol):
    def generate(self, brief: DesignBrief, facts: CandidateFactsSnapshot) -> list[ReviewItemDraft]: ...


class ClaimJudge(Protocol):
    def judge(self, brief: DesignBrief, facts: CandidateFactsSnapshot, draft: ReviewItemDraft) -> ClaimJudgement: ...


class _QueueMixin:
    def __init__(self, responses: list | None = None):
        self._responses = list(responses or [])
        self.calls: list[dict] = []

    def _next(self, role: str):
        if not self._responses:
            raise ExperienceProviderError(f"{role}: response queue exhausted")
        return self._responses.pop(0)


class FakeDesignGenerator(_QueueMixin):
    """Returns queued CandidateDraft values; never calls a model or network."""

    def generate(self, brief, *, round_number=1, count=None, n=None, prompt=None):
        count = count if count is not None else n
        if count is None:
            raise ExperienceProviderError("FakeDesignGenerator: count/n is required")
        self.calls.append(
            {"brief_revision_id": brief.revision_id, "round_number": round_number, "count": count, "prompt": prompt}
        )
        item = self._next("FakeDesignGenerator")
        if isinstance(item, list):
            values = item
        else:
            # Accept both a queued batch ([draft, ...]) and the more natural
            # one-response-per-candidate queue used by existing FakeProvider.
            values = [item]
            while len(values) < count and self._responses:
                values.append(self._next("FakeDesignGenerator"))
        if len(values) != count:
            raise ExperienceProviderError(
                f"FakeDesignGenerator: expected {count} candidates, got {len(values)}"
            )
        return [v if isinstance(v, CandidateDraft) else CandidateDraft.model_validate(v) for v in values]


class ManualImportGenerator:
    """Adapter for structured JSON/text exported by an external generator.

    It intentionally performs no generation and treats imported values as
    untrusted drafts; the application service still applies all gates.
    """

    def __init__(self, drafts: list[CandidateDraft | dict]):
        self.drafts = [d if isinstance(d, CandidateDraft) else CandidateDraft.model_validate(d) for d in drafts]
        self.calls: list[dict] = []

    def generate(self, brief, *, round_number=1, count=None, n=None, prompt=None):
        count = count if count is not None else n
        if count is None:
            raise ExperienceProviderError("ManualImportGenerator: count/n is required")
        self.calls.append({"brief_revision_id": brief.revision_id, "round_number": round_number, "count": count, "prompt": prompt})
        if len(self.drafts) != count:
            raise ExperienceProviderError(f"ManualImportGenerator: expected {count} candidates, got {len(self.drafts)}")
        values, self.drafts = self.drafts[:count], self.drafts[count:]
        return values


class ScaffoldDesignGenerator:
    """Deterministic generator for complete first-pass product concepts.

    The scaffold is deliberately text-first: it produces a coherent product
    concept, component breakdown, interaction flow, feedback policy, event
    sequences and canonical variables.  It does not claim CAD, manufacturability
    or measured physical properties.  A real generator can replace this class
    behind the same ``DesignGenerator`` protocol later.
    """

    _DIRECTIONS = ("quiet_control", "discoverable", "privacy_first", "low_attention", "recovery_first")
    _FORMS = ("desktop_device", "wearable", "handheld", "earbud_case", "portable_object")
    _MOBILE_FORMS = ("wearable", "handheld", "earbud_case", "phone_case", "portable_object")
    _MODALITIES = ("private_haptic", "visual", "in_ear_voice", "private_haptic", "visual")

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, brief: DesignBrief, *, round_number: int = 1, count: int | None = None, n: int | None = None, prompt: object | None = None) -> list[CandidateDraft]:
        requested = count if count is not None else n
        if requested is None:
            requested = brief.round_one_size if round_number == 1 else brief.round_two_variants_per_direction
        self.calls.append({"brief_revision_id": brief.revision_id, "round_number": round_number, "count": requested, "prompt": prompt})
        selected_parents = tuple(getattr(prompt, "selected_candidate_revision_ids", ()) or ())
        if round_number == 2 and len(selected_parents) == 0:
            raise ExperienceProviderError("ScaffoldDesignGenerator: second round requires selected parents")
        drafts: list[CandidateDraft] = []
        for index in range(requested):
            parent = selected_parents[index % len(selected_parents)] if selected_parents else None
            direction = self._DIRECTIONS[index % len(self._DIRECTIONS)]
            drafts.append(self._build_draft(brief, index + 1, direction, round_number, parent))
        return drafts

    def generate_design(self, brief: DesignBrief, *, round_number: int = 1, count: int | None = None, n: int | None = None, prompt: object | None = None) -> list[CandidateDraft]:
        """Semantic alias for clients asking for complete designs."""
        return self.generate(brief, round_number=round_number, count=count, n=n, prompt=prompt)

    def _build_draft(self, brief: DesignBrief, index: int, direction: str, round_number: int, parent: str | None) -> CandidateDraft:
        candidate_id = f"scaffold-r{round_number}-{index}"
        modality = self._MODALITIES[(index - 1) % len(self._MODALITIES)]
        form = self._form_factor(brief, index)
        wrist = form == "wearable"
        shape = DesignShape(
            form_factor=form,
            silhouette="low-profile rounded dorsal-wrist pod with no snagging protrusions" if wrist else "rounded compact body with a single visible status edge",
            interaction_surface="concave confirmation pad plus guarded recessed one-handed stop control" if wrist else "one tactile confirmation surface plus a recessed cancel gesture",
            feedback_surface=f"{modality} feedback channel with a wearer-facing state edge" if wrist else f"{modality} feedback channel with a low-salience status light",
            grip_or_mount="broad vented soft strap with keyed clasp and intentional quick release" if wrist else "desk stand or soft clip depending on form factor",
            material_hint="soft-touch polymer over a rigid internal shell",
            visible_state="wearer-facing state edge shows active/sensing state without content" if wrist else "thin status edge is off when private mode is active",
            body_placement="dorsal wrist, centered proximal to the wrist crease" if wrist else "near the user's hand, ear or clothing attachment point; exact placement is a design variable",
            attachment_strategy="broad vented strap with anti-rotation texture and intentional quick release" if wrist else "reversible clip, strap or desk stand selected by movement phase",
            motion_adaptation="detect movement phase transitions and reduce interaction complexity under motion",
            contact_area="broad compliant underside, avoiding wrist prominences" if wrist else None,
            mass_distribution="centered over wrist/forearm axis with no distal overhang" if wrist else None,
            feedback_modality=modality,
            feedback_timing="bounded pulse at a safe task boundary",
            confirmation_action="recessed press-hold; no response terminates routine event" if wrist else None,
            physical_unknowns=("exact dimensions", "weight distribution", "surface friction", "feedback detectability"),
        )
        design = DesignSpecification(
            design_id=f"{candidate_id}.design",
            title=f"{direction.replace('_', ' ').title()} Companion",
            concept_summary=f"A {form.replace('_', ' ')} in the {brief.product_category} category that helps during {brief.context} while preserving a clear user stop path.",
            problem_statement=f"{brief.target_segment} need support for {brief.goal} without losing task continuity, privacy or control.",
            user_value="Make an AI intervention legible, dismissible and recoverable without requiring sustained visual attention.",
            intended_user_and_context=f"{brief.target_segment} in {brief.context}; designed for the brief goal: {brief.goal}.",
            shape=shape,
            components=(
                DesignComponent(component_id=f"{candidate_id}.body", name="Main body", role="houses electronics and gives the object a stable silhouette", placement="central enclosure", material_or_finish="soft-touch polymer"),
                DesignComponent(component_id=f"{candidate_id}.surface", name="Confirmation surface", role="accepts an intentional user confirmation", placement="front-facing thumb zone", material_or_finish="slightly raised matte surface"),
                DesignComponent(component_id=f"{candidate_id}.status", name="Status edge", role="communicates private/active/snoozed state", placement="perimeter edge", material_or_finish="diffused indicator"),
            ),
            design_principles=(direction.replace("_", " "), "bounded intervention", "visible user control", "explicit failure recovery", *brief.design_language, *(f"brief tradeoff: {item}" for item in brief.tradeoff_priorities), *(f"movement rule candidate: {rule.recommendation}" for rule in brief.initial_design_rules)),
            functional_architecture=("context input adapter produces a bounded confidence declaration", "local policy gate decides whether intervention is allowed", "feedback controller executes one event sequence", "user response controller handles confirm, reject, snooze and correction", "event log records the declared state transition", *brief.required_capabilities),
            sensing_and_inference=("no emotion or clinical-state inference", "context inference exposes signal source and confidence", "low confidence follows a reduced-intervention path", "user correction invalidates the current inference for the active event"),
            movement_model=("represent movement as a bounded sequence of stationary, transition and active-motion phases", "re-evaluate hands, visual attention, social visibility and interruption cost at phase boundaries", "do not infer intent or consent from velocity, posture or route alone"),
            ergonomic_strategy=("keep mass and contact pressure explicit unknowns until prototype evidence", "use reversible attachment and a clear removal path", "preserve one-handed or hands-free rejection and stop paths when declared by the scenario"),
            adaptation_behavior=("reduce salience and persistence when motion or visual demand rises", "switch to private/non-visual feedback when public visibility or visual unavailability is declared", "terminate or request re-confirmation after a context correction"),
            material_and_finish=("soft-touch polymer shell", "matte diffused wearer-facing indicator", "vented compliant strap with cleanable contact surface") if wrist else ("soft-touch polymer shell", "matte diffused indicator", "replaceable clip or desk stand"),
            interaction_flow=("device receives a context-qualified event", "device presents one bounded signal", "user confirms, rejects, snoozes or corrects", "device terminates or enters a recovery path"),
            feedback_behavior=(f"primary modality: {modality}", "no repeated escalation after rejection", "snooze permits at most one bounded retry", "no response terminates or defers according to event policy"),
            privacy_and_control=("private feedback is preferred for routine events", "public output is not used for private content", "visible state shows when context inference is active", "correction immediately stops the current event", *(f"brief constraint: {item}" for item in brief.constraints), *(f"avoid prohibited experience: {item.operational_definition}" for item in brief.prohibited_experiences)),
            data_flow=("event metadata enters the local policy gate", "only the minimum event label and confidence are retained for the active event", "raw private content is not required for routine feedback", "no remote transfer is assumed in the scaffold"),
            power_and_connectivity=("local event policy remains available when connectivity is interrupted", "battery and radio budget are not yet measured"),
            safety_and_failure_modes=("false positive: user can correct and immediately terminate", "no response: routine intervention ends without implicit consent", "feedback not detectable: record uncertainty and use only an allowed low-cost fallback", "connectivity loss: retain local stop, reject and snooze controls", "component failure and thermal behavior require engineering validation"),
            manufacturing_assumptions=("single-piece outer shell is assumed", "component tolerances and ingress protection are unverified"),
            verification_plan=("review all four minimum intervention events", "compare signal detectability without increasing public exposure", "test rejection and correction paths for immediate termination", "measure mass, surface temperature, battery demand and control activation force on a prototype", *(rule.verification for rule in brief.initial_design_rules)),
            success_criteria=("all event branches terminate or recover within the bounded state machine", "routine private feedback exposes no private content publicly", "rejection prevents ordinary re-intervention in the same scope", "every claimed physical value is measured or remains explicitly unknown", *tuple(f"supports criterion: {criterion.name}" for criterion in brief.criteria)),
            declared_unknowns=shape.physical_unknowns + ("actual user preference", "long-term reliability"),
        )
        variable_ids = tuple(brief.divergence_matrix.variable_ids) or ("feedback.modality",)
        variables = [self._variable_value(variable_id, modality, direction, candidate_id) for variable_id in variable_ids]
        facts = [
            DeclaredFact(fact_id=f"{candidate_id}.fact.shape", subject="product", predicate="has_shape", value=shape.silhouette, source_locator="generated.design.shape"),
            DeclaredFact(fact_id=f"{candidate_id}.fact.modality", subject="product", predicate="uses_feedback_modality", value=modality, source_locator="generated.design.feedback_behavior"),
            DeclaredFact(fact_id=f"{candidate_id}.fact.control", subject="interaction", predicate="supports_correction", value="immediate stop and recovery", source_locator="generated.design.privacy_and_control", risk_relevance="control"),
        ]
        events = [self._event(candidate_id, event_type, brief.scenario_ids[0], modality) for event_type in ("normal_intervention", "defer_or_reject", "low_confidence", "misclassification_recovery")]
        return CandidateDraft(
            candidate_id=candidate_id,
            brief_revision_id=brief.revision_id,
            parent_candidate_revision_id=parent,
            source="fake_provider",
            name=design.title,
            description=design.concept_summary,
            interaction_story=" ".join(design.interaction_flow),
            target_context=design.intended_user_and_context,
            unknowns=list(design.declared_unknowns),
            strategy_direction=direction,
            changed_variable_ids=list(variable_ids),
            declared_facts=facts,
            variables=variables,
            events=events,
            generator_application_declarations={},
            shape=shape,
            design=design,
        )

    def _variable_value(self, variable_id: str, modality: str, direction: str, candidate_id: str) -> DesignVariableValue:
        # Keep the scaffold semantically useful when a brief asks to diverge
        # on physical variables.  Falling back to the strategy label would
        # make e.g. contact_area="quiet" look like a physical fact.
        defaults = {
            "feedback.modality": modality,
            "intervention.modality": modality,
            "feedback.timing": direction,
            "feedback.confirmation": direction,
            "wearable.form_factor": "wearable",
            "wearable.body_placement": "dorsal wrist",
            "wearable.attachment_strategy": "broad vented strap with intentional quick release",
            "wearable.attachment": "broad vented strap with intentional quick release",
            "wearable.contact_area": "broad compliant underside",
            "wearable.mass_distribution": "centered over wrist axis",
            "device.visible_state": "wearer-facing state edge",
            "control.cancel_action": "recessed one-handed press-hold",
        }
        enum_value = defaults.get(variable_id, direction)
        value_type = "enum"
        return DesignVariableValue(variable_id=variable_id, value_type=value_type, normalized_value=enum_value, display_value=str(enum_value), source_fact_id=f"{candidate_id}.fact.modality")

    def _form_factor(self, brief: DesignBrief, index: int) -> str:
        category = brief.product_category.lower()
        mobile_terms = ("wear", "穿戴", "移动", "mobile", "wearable", "耳机", "手持")
        forms = self._MOBILE_FORMS if any(term in category for term in mobile_terms) else self._FORMS
        return forms[(index - 1) % len(forms)]

    def _event(self, candidate_id: str, event_type: str, scenario_id: str, modality: str) -> InterventionEventSequence:
        branches = (
            ResponseBranch(response="user_rejected", condition="user explicitly rejects", outcome="termination"),
            ResponseBranch(response="user_snoozed", condition="user defers", outcome="recovery", resume_condition="next task boundary", max_retries=1),
            ResponseBranch(response="no_response", condition="response window expires", outcome="termination"),
            ResponseBranch(response="feedback_not_detectable", condition="detectability cannot be established", outcome="recovery"),
            ResponseBranch(response="user_corrected", condition="user marks context as wrong", outcome="recovery"),
        )
        return InterventionEventSequence(
            event_id=f"{candidate_id}.{event_type}",
            event_type=event_type,
            scenario_id=scenario_id,
            criticality="routine" if event_type != "low_confidence" else "important",
            trigger="a brief-qualified event is available",
            context_snapshot="current task, environment and social visibility snapshot",
            context_inference="declared context inference with confidence and correction path",
            permission_decision="routine intervention allowed only when user has not rejected this scope",
            feedback_steps=(EventStep(step_id=f"{candidate_id}.{event_type}.signal", modality=modality, timing="at the least disruptive task boundary", salience_level=1, duration_ms=300, repetition=0, variable_refs=("feedback.modality", "feedback.timing")),),
            expected_user_response="accept, reject, snooze, correct or no response",
            response_branches=branches,
            correction_path="stop current event and mark context corrected",
            recovery_path="return to the task without hidden escalation",
            termination_conditions=("accepted", "rejected", "timeout", "correction handled"),
        )


class FakeReviewReasoner(_QueueMixin):
    """Returns queued ReviewItemDraft values as untrusted review drafts."""

    def generate(self, brief, facts):
        self.calls.append({"brief_revision_id": brief.revision_id, "facts_snapshot_id": facts.facts_snapshot_id})
        item = self._next("FakeReviewReasoner")
        values = item if isinstance(item, list) else [item]
        return [v if isinstance(v, ReviewItemDraft) else ReviewItemDraft.model_validate(v) for v in values]

    def review(self, brief, facts):
        return self.generate(brief, facts)


class FakeClaimJudge(_QueueMixin):
    """Returns queued claim judgements; it cannot confirm or mutate ReviewItems."""

    def judge(self, brief, facts, draft):
        self.calls.append(
            {
                "brief_revision_id": brief.revision_id,
                "facts_snapshot_id": facts.facts_snapshot_id,
                "review_item_id": draft.review_item_id,
            }
        )
        item = self._next("FakeClaimJudge")
        return item if isinstance(item, ClaimJudgement) else ClaimJudgement.model_validate(item)

    def check(self, brief, facts, draft):
        return self.judge(brief, facts, draft)
