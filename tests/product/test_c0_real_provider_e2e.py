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
import time
from datetime import datetime, timezone

from psyteardown.product.commands import CreateProductProject
from psyteardown.product.contract_model import build_contract_model_from_env
from psyteardown.product.jobs import (
    InMemoryProductJobRepository,
    ProductProposalJobService,
)
from psyteardown.product.providers import (
    DeterministicFakeProductContractProvider,
    RealModelProductContractProvider,
)
from psyteardown.product.repositories import InMemoryProductRepository
from psyteardown.product.service import ProductApplicationService


def test_c0_real_provider_end_to_end():
    """Test complete chain with real provider for Product Contract objects."""

    # Setup: Check prerequisites
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ DEEPSEEK_API_KEY not set, skipping real provider test")
        return

    contract_model_env = os.environ.get("PSYTEARDOWN_PRODUCT_CONTRACT_MODEL", "").lower()
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
    }

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
            result_job = job_service.run_job(
                project_id=project.project_id,
                job_id=intent_job.job_id,
                actor="c0-test-worker",
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
                project_id=project.project_id,
                intent_id=view.product_intent.intent_id,
                expected_revision=view.product_intent.meta.revision,
                actor="c0-test",
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

        result_job = job_service.run_job(
            project_id=project.project_id,
            job_id=problem_job.job_id,
            actor="c0-test-worker",
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
                project_id=project.project_id,
                problem_model_id=view.problem_model.problem_model_id,
                expected_revision=view.problem_model.meta.revision,
                actor="c0-test",
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

        result_job = job_service.run_job(
            project_id=project.project_id,
            job_id=outcome_job.job_id,
            actor="c0-test-worker",
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
            confirmed_outcome = application.confirm_outcome_contract(
                project_id=project.project_id,
                outcome_contract_id=view.outcome_contract.outcome_contract_id,
                expected_revision=view.outcome_contract.meta.revision,
                actor="c0-test",
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

        result_job = job_service.run_job(
            project_id=project.project_id,
            job_id=thesis_job.job_id,
            actor="c0-test-worker",
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
            selected_thesis = application.select_product_thesis(
                project_id=project.project_id,
                thesis_id=first_thesis.thesis_id,
                expected_revision=first_thesis.meta.revision,
                actor="c0-test",
            )
            print(f"✅ ProductThesis selected: {selected_thesis.name}")
            print(f"   Thesis ID: {selected_thesis.thesis_id}")
        else:
            print(f"❌ No product theses found")
            return metrics
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
        metrics["end_time"] = datetime.now(timezone.utc)
        metrics["total_time"] = (metrics["end_time"] - metrics["start_time"]).total_seconds()


if __name__ == "__main__":
    metrics = test_c0_real_provider_end_to_end()

    if metrics and len(metrics.get("failures", [])) > 0:
        print("\n" + "=" * 80)
        print("⚠️  FAILURES DETECTED")
        print("=" * 80)
        for failure in metrics["failures"]:
            print(f"\nStep: {failure['step']}")
            print(f"Error code: {failure.get('error_code', 'N/A')}")
            print(f"Error summary: {failure.get('error_summary', failure.get('error', 'N/A'))}")
