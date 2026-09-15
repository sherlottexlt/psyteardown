"""Quarantine and clean-rerun boundaries for ADRs 0424--0428.

The helpers in this module only record facts and enforce fail-closed state
transitions.  They intentionally do not decide candidate ranking, selection
lineage validity, or any post-428 qualification rule.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    CleanRerunClosure,
    CleanRerunRecord,
    ContaminationMark,
    DependencyRef,
    UnauthorizedOutput,
)


def quarantine_output(
    *,
    output_id: str,
    revision_id: str,
    output_type: str,
    execution_id: str,
    access_control: str,
    isolation_state: str = "quarantined",
    deletion_or_isolation_proof: str | None = None,
    impact_analysis_id: str | None = None,
) -> UnauthorizedOutput:
    """Record an unauthorized execution output as quarantined.

    The function has no ``viewed``/``adopted`` escape hatch: an output is
    quarantined even when no human has inspected it.
    """

    return UnauthorizedOutput(
        output_id=output_id,
        revision_id=revision_id,
        output_type=output_type,
        execution_id=execution_id,
        access_control=access_control,
        isolation_state=isolation_state,
        deletion_or_isolation_proof=deletion_or_isolation_proof,
        impact_analysis_id=impact_analysis_id,
    )


def propagate_contamination(
    *,
    object_id: str,
    revision_id: str,
    object_type: str,
    source_output_ids: Iterable[str],
    dependencies: Iterable[DependencyRef] = (),
    access_evidence: Iterable[str] = (),
) -> ContaminationMark:
    """Mark a downstream object contaminated when it read quarantined output.

    Callers should invoke this for every direct/indirect lineage descendant;
    the helper deliberately does not infer graph reachability from IDs.
    """

    sources = tuple(dict.fromkeys(source_output_ids))
    if not sources:
        raise ValueError("contamination requires at least one source output")
    return ContaminationMark(
        object_id=object_id,
        revision_id=revision_id,
        object_type=object_type,
        source_output_ids=sources,
        dependencies=tuple(dependencies),
        access_evidence=tuple(access_evidence),
    )


def build_clean_rerun(
    *,
    rerun_id: str,
    revision_id: str,
    source_object_id: str,
    source_revision_id: str,
    new_object_id: str,
    new_object_revision_id: str,
    closure: CleanRerunClosure,
    source_payload_hash: str,
    rerun_payload_hash: str,
    key_results_consistent: bool | None,
    lineage: Iterable[DependencyRef] = (),
    impact_analysis_id: str | None = None,
) -> CleanRerunRecord:
    """Create a clean-rerun revision with ADR 0426/0427/0428 state.

    Incomplete input closure is always ``clean_rerun_contamination_uncertain``.
    Complete closure plus equal payload/results is ``clean_rederived``.  A
    differing payload is divergence and requires an impact-analysis reference;
    it is never promoted to current by this helper.
    """

    if not closure.complete or key_results_consistent is None:
        status = "clean_rerun_contamination_uncertain"
        impact_required = False
    elif source_payload_hash != rerun_payload_hash or key_results_consistent is not True:
        status = "clean_rederivation_divergence"
        impact_required = True
        if not impact_analysis_id:
            raise ValueError("divergent clean rerun requires impact_analysis_id")
    else:
        status = "clean_rederived"
        impact_required = False
    return CleanRerunRecord(
        rerun_id=rerun_id,
        revision_id=revision_id,
        source_object_id=source_object_id,
        source_revision_id=source_revision_id,
        new_object_id=new_object_id,
        new_object_revision_id=new_object_revision_id,
        closure=closure,
        status=status,
        source_payload_hash=source_payload_hash,
        rerun_payload_hash=rerun_payload_hash,
        key_results_consistent=key_results_consistent,
        impact_analysis_required=impact_required,
        impact_analysis_id=impact_analysis_id,
        confirmed=status == "clean_rederived",
        lineage=tuple(lineage),
    )


__all__ = [
    "build_clean_rerun",
    "propagate_contamination",
    "quarantine_output",
]
