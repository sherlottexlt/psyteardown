"""C0 Stage 5: End-to-end real provider integration test.

This script tests the complete chain from ProductIntent to delivery bundle
using real model providers (DeepSeek) instead of fake providers.

Prerequisites:
- DEEPSEEK_API_KEY environment variable must be set
- PSYTEARDOWN_PRODUCT_CONTRACT_MODEL=deepseek

Test flow:
1. Create project with real provider
2. Generate ProductIntent using real model
3. Confirm ProductIntent
4. Generate ProblemModel using real model
5. Confirm ProblemModel
6. Generate OutcomeContract using real model
7. Confirm OutcomeContract
8. Generate ProductThesis candidates using real model
9. Select one thesis
10. Generate Web generation contract (fake provider for now)
11. Generate source code (B7m - can use real model if configured)
12. Execute and verify (B4)
13. Export delivery bundle (B6)
14. Record costs, timing, and failures

Expected outcomes:
- At least one successful end-to-end run
- Cost/token metrics recorded
- Failure modes documented
"""

from __future__ import annotations

import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from psyteardown.product.commands import CreateProductProject
from psyteardown.product.commands import (
    ConfirmOutcomeContract,
    ConfirmProblemModel,
    ConfirmProductIntent,
    ConfirmWebProductGenerationContract,
    OutcomeContractProposal,
    SubmitOutcomeContractProposal,
    TransitionProductThesis,
)
from psyteardown.product.contract_model import build_contract_model_from_env
from psyteardown.product.jobs import (
    InMemoryProductJobRepository,
    ProductProposalJobService,
)
from psyteardown.product.providers import (
    DeterministicFakeProductContractProvider,
    RealModelProductContractProvider,
)
from psyteardown.product.env import get_project_env
from psyteardown.product.source_model import build_source_model_from_env
from psyteardown.product.generation import (
    InMemoryProductGenerationJobRepository,
    ProductGenerationJobService,
)
from psyteardown.product.execution import (
    InMemoryProductExecutionJobRepository,
    ProductExecutionJobService,
)
from psyteardown.product.delivery import (
    InMemoryProductDeliveryBundleRepository,
    ProductDeliveryBundleService,
)
from psyteardown.product.repositories import InMemoryProductRepository
from psyteardown.product.service import ProductApplicationService
from psyteardown.product.models import ExecutionBudget


def _run_with_bounded_retry(service, project_id: str, job, *, actor: str, metrics: dict, step: str, max_retries: int = 1):
    """Run a job and perform at most one explicit, measured retry.

    C0 remains a single-attempt integration probe by default. C3 opts into this
    helper so the already-approved per-job retry budgets are exercised without
    silently repeating an entire end-to-end run.
    """
    current = service.run_job(project_id=project_id, job_id=job.job_id, actor=actor)
    retries = 0
    while current.status in {"failed", "budget_exhausted", "stale_input"} and retries < max_retries:
        retry_requested = service.retry_job(project_id, current.job_id, actor=actor)
        if retry_requested.status != "queued":
            break
        failure_code = current.error_code or "unknown_failure"
        retries += 1
        current = service.run_job(project_id=project_id, job_id=current.job_id, actor=actor)
        if current.status == "succeeded":
            metrics.setdefault("recovered_failures", []).append({
                "step": step,
                "error_code": failure_code,
            })
    return current


def _build_model_usage(real_provider, generated) -> dict:
    contract_calls = list(getattr(real_provider, "usage_records", ()))
    source_calls = [
        {
            "provider": call.provider,
            "model": call.model,
            "outcome": call.outcome,
            "input_tokens": call.input_tokens,
            "output_tokens": call.output_tokens,
            "duration_seconds": call.duration_seconds,
        }
        for call in (getattr(generated, "model_calls", ()) if generated is not None else ())
    ]
    all_calls = contract_calls + source_calls
    return {
        "contract_provider": contract_calls,
        "source_provider": source_calls,
        "total_calls": len(all_calls),
        "input_tokens": sum((item.get("input_tokens") or 0) for item in all_calls),
        "output_tokens": sum((item.get("output_tokens") or 0) for item in all_calls),
        "monetary_cost": None,
    }


def _run_c0_real_provider_end_to_end(*, bounded_retries: bool = False, output_root: Path | None = None):
    """Test complete chain with real provider for Product Contract objects."""

    # Setup: Check prerequisites
    api_key = get_project_env("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY not set, skipping real provider test")
        return

    contract_model_env = (
        get_project_env("PSYTEARDOWN_PRODUCT_CONTRACT_MODEL")
        or get_project_env("PSYTEARDOWN_LLM", "")
    ).lower()
    if contract_model_env != "deepseek":
        print(f"ℹ️  PSYTEARDOWN_PRODUCT_CONTRACT_MODEL={contract_model_env}, setting to 'deepseek'")
        os.environ["PSYTEARDOWN_PRODUCT_CONTRACT_MODEL"] = "deepseek"

    print("✅ Prerequisites met: DEEPSEEK_API_KEY configured")
    print()

    # Initialize services
    repository = InMemoryProductRepository()
    application = ProductApplicationService(repository=repository)
    job_repository = InMemoryProductJobRepository()

    # Initialize providers
    fake_provider = DeterministicFakeProductContractProvider()
    try:
        real_provider = RealModelProductContractProvider()
        print(f"✅ Real provider initialized: {real_provider.name} v{real_provider.version}")
    except Exception as e:
        print(f"❌ Failed to initialize real provider: {e}")
        return

    job_service = ProductProposalJobService(
        application=application,
        job_repository=job_repository,
        provider=fake_provider,
        real_provider=real_provider,
    )

    print()
    print("=" * 80)
    print("C0 Stage 5: Real Provider End-to-End Test")
    print("=" * 80)
    print()

    # Metrics tracking
    metrics = {
        "start_time": datetime.now(timezone.utc),
        "steps": [],
        "total_cost": 0,
        "failures": [],
        "recovered_failures": [],
    }
    generated = None

    try:
        # Step 1: Create project
        print("Step 1: Creating project...")
        step_start = time.time()
        project = application.create_project(
            CreateProductProject(
                actor="c0-test",
                reason="C0 stage 5 end-to-end test",
                name="C0 Real Provider Test",
            )
        )
        metrics["project_id"] = project.project_id
        step_time = time.time() - step_start
        print(f"✅ Project created: {project.project_id} ({step_time:.2f}s)")
        metrics["steps"].append({"step": "create_project", "time": step_time, "success": True})
        print()

        # Step 2: Generate ProductIntent with real provider
        print("Step 2: Generating ProductIntent with real provider...")
        raw_input = """I want to help knowledge workers maintain deep focus during work sessions.
They get interrupted frequently by messages and notifications, breaking their concentration.
This should work offline and not involve any employee monitoring or productivity scoring."""

        step_start = time.time()
        intent_job = job_service.create_job(
            project_id=project.project_id,
            kind="product_intent",
            actor="c0-test",
            reason="C0 stage 5 test: real provider",
            raw_input=raw_input,
            provider="real",  # ← Use real provider
        )
        print(f"✅ Intent job created: {intent_job.job_id}")
        print(f"   Provider: {intent_job.provider} v{intent_job.provider_version}")

        # Run the job
        try:
            result_job = _run_with_bounded_retry(
                job_service,
                project.project_id,
                intent_job,
                actor="c0-test-worker",
                metrics=metrics,
                step="generate_intent",
                max_retries=1 if bounded_retries else 0,
            )
        except Exception as e:
            print(f"❌ Exception during job execution: {e}")
            import traceback
            traceback.print_exc()
            metrics["failures"].append({
                "step": "generate_intent",
                "error": str(e),
                "traceback": traceback.format_exc(),
            })
            return metrics

        step_time = time.time() - step_start

        if result_job.status == "succeeded":
            print(f"✅ ProductIntent generated successfully ({step_time:.2f}s)")
            print(f"   Result revision: {result_job.result_revision_id}")
            metrics["steps"].append({
                "step": "generate_intent",
                "time": step_time,
                "success": True,
                "provider": "real",
            })
        else:
            print(f"❌ Intent job failed: {result_job.status}")
            print(f"   Error: {result_job.error_code} - {result_job.error_summary}")
            metrics["steps"].append({
                "step": "generate_intent",
                "time": step_time,
                "success": False,
                "error": f"{result_job.error_code}: {result_job.error_summary}",
            })
            metrics["failures"].append({
                "step": "generate_intent",
                "error_code": result_job.error_code,
                "error_summary": result_job.error_summary,
            })
            print("\n⚠️  Stopping test due to Intent generation failure")
            return metrics
        print()

        # Step 3: Confirm ProductIntent
        print("Step 3: Confirming ProductIntent...")
        view = application.get_project_view(project.project_id)
        if view.product_intent and view.product_intent.status == "proposed":
            confirmed_intent = application.confirm_product_intent(
                ConfirmProductIntent(
                    project_id=project.project_id,
                intent_id=view.product_intent.intent_id,
                expected_revision=view.product_intent.meta.revision,
                actor="c0-test",
                    reason="C0 real provider proposal reviewed",
                )
            )
            print(f"✅ ProductIntent confirmed: {confirmed_intent.revision_id}")
        else:
            print(f"❌ No proposed intent found")
            return metrics
        print()

        # Step 4: Generate ProblemModel with real provider
        print("Step 4: Generating ProblemModel with real provider...")
        step_start = time.time()
        problem_job = job_service.create_job(
            project_id=project.project_id,
            kind="problem_model",
            actor="c0-test",
            reason="C0 stage 5 test: real provider",
            provider="real",  # ← Use real provider
        )

        result_job = _run_with_bounded_retry(
            job_service,
            project.project_id,
            problem_job,
            actor="c0-test-worker",
            metrics=metrics,
            step="generate_problem",
            max_retries=1 if bounded_retries else 0,
        )
        step_time = time.time() - step_start

        if result_job.status == "succeeded":
            print(f"✅ ProblemModel generated successfully ({step_time:.2f}s)")
            metrics["steps"].append({
                "step": "generate_problem",
                "time": step_time,
                "success": True,
                "provider": "real",
            })
        else:
            print(f"❌ Problem job failed: {result_job.status}")
            print(f"   Error: {result_job.error_code} - {result_job.error_summary}")
            metrics["steps"].append({
                "step": "generate_problem",
                "time": step_time,
                "success": False,
                "error": f"{result_job.error_code}: {result_job.error_summary}",
            })
            metrics["failures"].append({
                "step": "generate_problem",
                "error_code": result_job.error_code,
                "error_summary": result_job.error_summary,
            })
            print("\n⚠️  Stopping test due to ProblemModel generation failure")
            return metrics
        print()

        # Step 5: Confirm ProblemModel
        print("Step 5: Confirming ProblemModel...")
        view = application.get_project_view(project.project_id)
        if view.problem_model and view.problem_model.status == "proposed":
            confirmed_problem = application.confirm_problem_model(
                ConfirmProblemModel(
                    project_id=project.project_id,
                problem_model_id=view.problem_model.problem_model_id,
                expected_revision=view.problem_model.meta.revision,
                actor="c0-test",
                    reason="C0 real provider proposal reviewed",
                )
            )
            print(f"✅ ProblemModel confirmed: {confirmed_problem.revision_id}")
        else:
            print(f"❌ No proposed problem model found")
            return metrics
        print()

        # Step 6: Generate OutcomeContract with real provider
        print("Step 6: Generating OutcomeContract with real provider...")
        step_start = time.time()
        outcome_job = job_service.create_job(
            project_id=project.project_id,
            kind="outcome_contract",
            actor="c0-test",
            reason="C0 stage 5 test: real provider",
            provider="real",  # ← Use real provider
        )

        result_job = _run_with_bounded_retry(
            job_service,
            project.project_id,
            outcome_job,
            actor="c0-test-worker",
            metrics=metrics,
            step="generate_outcome",
            max_retries=1 if bounded_retries else 0,
        )
        step_time = time.time() - step_start

        if result_job.status == "succeeded":
            print(f"✅ OutcomeContract generated successfully ({step_time:.2f}s)")
            metrics["steps"].append({
                "step": "generate_outcome",
                "time": step_time,
                "success": True,
                "provider": "real",
            })
        else:
            print(f"❌ Outcome job failed: {result_job.status}")
            print(f"   Error: {result_job.error_code} - {result_job.error_summary}")
            metrics["steps"].append({
                "step": "generate_outcome",
                "time": step_time,
                "success": False,
                "error": f"{result_job.error_code}: {result_job.error_summary}",
            })
            metrics["failures"].append({
                "step": "generate_outcome",
                "error_code": result_job.error_code,
                "error_summary": result_job.error_summary,
            })
            print("\n⚠️  Stopping test due to OutcomeContract generation failure")
            return metrics
        print()

        # Step 7: Confirm OutcomeContract
        print("Step 7: Confirming OutcomeContract...")
        view = application.get_project_view(project.project_id)
        if view.outcome_contract and view.outcome_contract.status == "proposed":
            reviewed = OutcomeContractProposal.model_validate(
                view.outcome_contract.model_dump(
                    mode="python",
                    exclude={
                        "outcome_contract_id",
                        "revision_id",
                        "meta",
                        "project_id",
                        "status",
                        "dependencies",
                        "confirmation",
                    },
                )
            ).model_copy(update={"prohibited_outcomes_reviewed": True})
            reviewed_contract = application.submit_outcome_contract(
                SubmitOutcomeContractProposal(
                    project_id=project.project_id,
                    outcome_contract_id=view.outcome_contract.outcome_contract_id,
                    expected_revision=view.outcome_contract.meta.revision,
                    proposal=reviewed,
                    actor="c0-test",
                    reason="C0 real provider prohibited outcomes reviewed",
                )
            )
            confirmed_outcome = application.confirm_outcome_contract(
                ConfirmOutcomeContract(
                    project_id=project.project_id,
                outcome_contract_id=reviewed_contract.outcome_contract_id,
                expected_revision=reviewed_contract.meta.revision,
                actor="c0-test",
                    reason="C0 real provider proposal reviewed",
                )
            )
            print(f"✅ OutcomeContract confirmed: {confirmed_outcome.revision_id}")
        else:
            print(f"❌ No proposed outcome contract found")
            return metrics
        print()

        # Step 8: Generate ProductThesis with real provider
        print("Step 8: Generating ProductThesis candidates with real provider...")
        step_start = time.time()
        thesis_job = job_service.create_job(
            project_id=project.project_id,
            kind="product_theses",
            actor="c0-test",
            reason="C0 stage 5 test: real provider",
            provider="real",  # ← Use real provider
        )

        result_job = _run_with_bounded_retry(
            job_service,
            project.project_id,
            thesis_job,
            actor="c0-test-worker",
            metrics=metrics,
            step="generate_theses",
            max_retries=1 if bounded_retries else 0,
        )
        step_time = time.time() - step_start

        if result_job.status == "succeeded":
            print(f"✅ ProductThesis candidates generated successfully ({step_time:.2f}s)")
            print(f"   Generated {len(result_job.result_revision_ids)} theses")
            metrics["steps"].append({
                "step": "generate_theses",
                "time": step_time,
                "success": True,
                "provider": "real",
                "thesis_count": len(result_job.result_revision_ids),
            })
        else:
            print(f"❌ Thesis job failed: {result_job.status}")
            print(f"   Error: {result_job.error_code} - {result_job.error_summary}")
            metrics["steps"].append({
                "step": "generate_theses",
                "time": step_time,
                "success": False,
                "error": f"{result_job.error_code}: {result_job.error_summary}",
            })
            metrics["failures"].append({
                "step": "generate_theses",
                "error_code": result_job.error_code,
                "error_summary": result_job.error_summary,
            })
            print("\n⚠️  Stopping test due to ProductThesis generation failure")
            return metrics
        print()

        # Step 9: Select first thesis
        print("Step 9: Selecting ProductThesis...")
        view = application.get_project_view(project.project_id)
        if view.product_theses:
            first_thesis = view.product_theses[0]
            selected_thesis = application.transition_product_thesis(
                TransitionProductThesis(
                    project_id=project.project_id,
                    thesis_id=first_thesis.thesis_id,
                    expected_revision=first_thesis.meta.revision,
                    to_status="selected",
                    actor="c0-test",
                    actor_type="human",
                    reason="C0 real provider thesis selected",
                )
            )
            print(f"✅ ProductThesis selected: {selected_thesis.name}")
            print(f"   Thesis ID: {selected_thesis.thesis_id}")
        else:
            print(f"❌ No product theses found")
            return metrics
        print()

        # Step 10: Generate and confirm the Web generation contract. The
        # contract provider is intentionally deterministic here; C0's real
        # provider boundary is Product Contract, while B7m owns real source.
        print("Step 10: Generating Web generation contract...")
        step_start = time.time()
        web_job = job_service.create_job(
            project_id=project.project_id,
            kind="web_generation_contract",
            actor="c0-test",
            reason="C0 real chain Web realization",
            provider="deterministic_fake",
        )
        result_job = job_service.run_job(
            project_id=project.project_id,
            job_id=web_job.job_id,
            actor="c0-test-worker",
        )
        step_time = time.time() - step_start
        if result_job.status != "succeeded":
            print(f"❌ Web contract job failed: {result_job.error_code} - {result_job.error_summary}")
            metrics["failures"].append({
                "step": "generate_web_contract",
                "error_code": result_job.error_code,
                "error_summary": result_job.error_summary,
            })
            return metrics
        view = application.get_project_view(project.project_id)
        draft = view.web_generation_contract
        if draft is None:
            print("❌ No Web generation contract proposal found")
            return metrics
        confirmed_web = application.confirm_web_generation_contract(
            ConfirmWebProductGenerationContract(
                project_id=project.project_id,
                web_generation_contract_id=draft.web_generation_contract_id,
                expected_revision=draft.meta.revision,
                actor="c0-test",
                reason="C0 Web generation boundary reviewed",
            )
        )
        print(f"✅ Web generation contract confirmed: {confirmed_web.revision_id} ({step_time:.2f}s)")
        metrics["steps"].append({
            "step": "generate_web_contract",
            "time": step_time,
            "success": True,
            "provider": "deterministic_fake",
        })
        print()

        # Step 11: B7m real model source generation.
        print("Step 11: Generating Web source with real model...")
        source_model = build_source_model_from_env()
        if source_model is None:
            print("❌ Real source model is unavailable")
            metrics["failures"].append({
                "step": "generate_source",
                "error_code": "source_model_unavailable",
                "error_summary": "PSYTEARDOWN_PRODUCT_SOURCE_MODEL/PSYTEARDOWN_LLM is not configured.",
            })
            return metrics
        run_root = (output_root or Path("output/product-studio/c0-real-provider")) / project.project_id
        generation_repository = InMemoryProductGenerationJobRepository()
        generation_service = ProductGenerationJobService(
            application,
            generation_repository,
            workspace_root=run_root / "workspaces",
            transcript_root=run_root / "model-calls",
            source_model=source_model,
        )
        step_start = time.time()
        generation_job = generation_service.create_job(
            project_id=project.project_id,
            actor="c0-test",
            reason="C0 real model source generation",
            source="model",
        )
        generated = _run_with_bounded_retry(
            generation_service,
            project.project_id,
            generation_job,
            actor="c0-test-worker",
            metrics=metrics,
            step="generate_source",
            max_retries=1 if bounded_retries else 0,
        )
        step_time = time.time() - step_start
        if generated.status != "succeeded":
            print(f"❌ Source generation failed: {generated.error_code} - {generated.error_summary}")
            metrics["steps"].append({
                "step": "generate_source",
                "time": step_time,
                "success": False,
                "provider": generated.provider,
                "model_calls": [
                    {"input_tokens": call.input_tokens, "output_tokens": call.output_tokens, "outcome": call.outcome}
                    for call in generated.model_calls
                ],
            })
            metrics["failures"].append({
                "step": "generate_source",
                "error_code": generated.error_code,
                "error_summary": generated.error_summary,
            })
            return metrics
        source_tokens = [
            {"input_tokens": call.input_tokens, "output_tokens": call.output_tokens, "outcome": call.outcome}
            for call in generated.model_calls
        ]
        print(f"✅ Real source generated and statically gated ({step_time:.2f}s)")
        print(f"   Model calls: {source_tokens}")
        metrics["steps"].append({
            "step": "generate_source",
            "time": step_time,
            "success": True,
            "provider": generated.provider,
            "model_calls": source_tokens,
        })
        print()

        # Step 12: B4 real local subprocess build/preview/browser validation.
        print("Step 12: Executing B4 build and browser validation...")
        execution_repository = InMemoryProductExecutionJobRepository(generation_repository)
        execution_service = ProductExecutionJobService(
            application,
            execution_repository,
            generation_repository,
            workspace_root=run_root / "workspaces",
        )
        step_start = time.time()
        execution_job = execution_service.create_job(
            project_id=project.project_id,
            generation_job_id=generated.job_id,
            actor="c0-test",
            reason="C0 real chain validation",
            budget=ExecutionBudget(max_attempts=2) if bounded_retries else None,
        )
        executed = _run_with_bounded_retry(
            execution_service,
            project.project_id,
            execution_job,
            actor="c0-test-worker",
            metrics=metrics,
            step="execute_b4",
            max_retries=1 if bounded_retries else 0,
        )
        step_time = time.time() - step_start
        if executed.status != "succeeded":
            print(f"❌ B4 execution failed: {executed.error_code} - {executed.error_summary}")
            metrics["steps"].append({
                "step": "execute_b4",
                "time": step_time,
                "success": False,
                "provider": executed.provider,
                "execution_steps": [step.status for step in executed.steps],
            })
            metrics["failures"].append({
                "step": "execute_b4",
                "error_code": executed.error_code,
                "error_summary": executed.error_summary,
            })
            return metrics
        print(f"✅ B4 build, preview and browser validation succeeded ({step_time:.2f}s)")
        metrics["steps"].append({
            "step": "execute_b4",
            "time": step_time,
            "success": True,
            "provider": executed.provider,
            "execution_steps": [step.status for step in executed.steps],
        })
        print()

        # Step 13: B6 content-addressed delivery bundle.
        print("Step 13: Exporting B6 delivery bundle...")
        bundle_repository = InMemoryProductDeliveryBundleRepository()
        delivery_service = ProductDeliveryBundleService(
            application,
            bundle_repository,
            generation_repository,
            execution_repository,
            workspace_root=run_root / "workspaces",
            export_root=run_root / "exports",
        )
        step_start = time.time()
        bundle = delivery_service.create_bundle(
            project_id=project.project_id,
            execution_job_id=executed.job_id,
            actor="c0-test",
            reason="C0 real chain delivery",
        )
        step_time = time.time() - step_start
        print(f"✅ B6 delivery bundle exported ({step_time:.2f}s)")
        print(f"   Bundle: {bundle.bundle_id}")
        print(f"   Archive sha256: {bundle.archive_sha256}")
        print(f"   Archive bytes: {bundle.archive_bytes}")
        metrics["steps"].append({
            "step": "export_b6",
            "time": step_time,
            "success": True,
            "archive_sha256": bundle.archive_sha256,
            "archive_bytes": bundle.archive_bytes,
        })
        print()

        # Stage 6: retain a local, machine-readable run report. Monetary cost
        # is intentionally not inferred; C0 records call count and tokens only.
        metrics["model_usage"] = _build_model_usage(real_provider, generated)
        report_path = run_root / "c0-metrics.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "run_date": datetime.now(timezone.utc).isoformat(),
                    "project_id": project.project_id,
                    "steps": metrics["steps"],
                    "model_usage": metrics["model_usage"],
                    "failures": metrics["failures"],
                    "recovered_failures": metrics.get("recovered_failures", []),
                    "total_time_seconds": (datetime.now(timezone.utc) - metrics["start_time"]).total_seconds(),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        print("Stage 6: Cost and failure analysis")
        print(f"- Model calls: {metrics['model_usage']['total_calls']}")
        print(f"- Input tokens: {metrics['model_usage']['input_tokens']}")
        print(f"- Output tokens: {metrics['model_usage']['output_tokens']}")
        print("- Monetary cost: not calculated by C0 policy")
        print(f"- Failure count in this run: {len(metrics['failures'])}")
        print(f"- Metrics report: {report_path}")
        print()

        print("=" * 80)
        print("✅ C0 Stage 5: Real Provider Chain SUCCESSFUL")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"- Total steps: {len(metrics['steps'])}")
        print(f"- Successful steps: {sum(1 for s in metrics['steps'] if s['success'])}")
        print(f"- Failed steps: {len(metrics['failures'])}")
        print(f"- Total time: {(datetime.now(timezone.utc) - metrics['start_time']).total_seconds():.2f}s")
        print()

        if metrics["steps"]:
            print("Step timings:")
            for step in metrics["steps"]:
                status = "✅" if step["success"] else "❌"
                provider = f" (provider={step.get('provider', 'N/A')})" if "provider" in step else ""
                print(f"  {status} {step['step']}: {step['time']:.2f}s{provider}")

        return metrics

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        metrics["failures"].append({
            "step": "unexpected",
            "error": str(e),
        })
        return metrics
    finally:
        metrics["model_usage"] = _build_model_usage(real_provider, generated)
        metrics["end_time"] = datetime.now(timezone.utc)
        metrics["total_time"] = (metrics["end_time"] - metrics["start_time"]).total_seconds()


def test_c0_real_provider_end_to_end():
    metrics = _run_c0_real_provider_end_to_end()
    if metrics is None:
        pytest.skip("DEEPSEEK_API_KEY is not configured")
    assert not metrics["failures"], metrics["failures"]


if __name__ == "__main__":
    metrics = _run_c0_real_provider_end_to_end()

    if metrics and len(metrics.get("failures", [])) > 0:
        print("\n" + "=" * 80)
        print("⚠️  FAILURES DETECTED")
        print("=" * 80)
        for failure in metrics["failures"]:
            print(f"\nStep: {failure['step']}")
            print(f"Error code: {failure.get('error_code', 'N/A')}")
            print(f"Error summary: {failure.get('error_summary', failure.get('error', 'N/A'))}")
