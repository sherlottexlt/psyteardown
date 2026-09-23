from collections import defaultdict
from datetime import datetime, timezone

import pytest

from psyteardown.product import (
    ExecutionBudget,
    InMemoryProductExecutionJobRepository,
    ProductExecutionJobService,
)
from psyteardown.product.execution import CommandResult
from .test_generation import build_generation_services


NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


class SequenceIds:
    def __init__(self) -> None:
        self.counts = defaultdict(int)

    def __call__(self, prefix: str) -> str:
        self.counts[prefix] += 1
        return f"{prefix}-{self.counts[prefix]}"


class FakeRunner:
    def __init__(self, *, failure: str | None = None, output_bytes: int = 0) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.envs: list[dict[str, str]] = []
        self.failure = failure
        self.output_bytes = output_bytes

    def run(self, argv, *, cwd, timeout, env):
        self.calls.append(tuple(argv))
        self.envs.append(dict(env))
        name = "install" if "install" in argv else "build"
        if self.failure == name:
            from psyteardown.product.execution import ExecutionCommandError

            raise ExecutionCommandError("command_failed", "The allowlisted command failed.", output_bytes=self.output_bytes)
        return CommandResult(exit_code=0, output_bytes=self.output_bytes, duration_seconds=0.01, summary="ok")

    def run_preview_and_browser(self, *, preview_argv, browser_argv, cwd, timeout, env):
        self.calls.extend((tuple(preview_argv), tuple(browser_argv)))
        self.envs.extend((dict(env), dict(env)))
        return (
            CommandResult(exit_code=0, output_bytes=self.output_bytes, duration_seconds=0.01, summary="preview"),
            CommandResult(exit_code=0, output_bytes=self.output_bytes, duration_seconds=0.01, summary="browser"),
        )


def build_execution_service(tmp_path, *, runner=None):
    application, _, generation, project, _ = build_generation_services(tmp_path / "workspaces")
    generated = generation.create_job(project_id=project.project_id, actor="user", reason="generate")
    generated = generation.run_job(project.project_id, generated.job_id, actor="worker")
    assert generated.status == "succeeded"
    repository = InMemoryProductExecutionJobRepository(generation.job_repository)
    service = ProductExecutionJobService(
        application,
        repository,
        generation.job_repository,
        workspace_root=tmp_path / "workspaces",
        clock=lambda: NOW,
        id_factory=SequenceIds(),
        command_runner=runner or FakeRunner(),
    )
    return service, project, generated


def test_execution_is_separate_from_generation_and_runs_allowlisted_steps(tmp_path):
    runner = FakeRunner()
    service, project, generated = build_execution_service(tmp_path, runner=runner)
    queued = service.create_job(
        project_id=project.project_id,
        generation_job_id=generated.job_id,
        actor="user",
        reason="validate",
    )
    completed = service.run_job(project.project_id, queued.job_id, actor="worker")
    assert completed.status == "succeeded"
    assert [step.name for step in completed.steps] == ["install", "build", "run", "browser"]
    assert all(step.status == "succeeded" for step in completed.steps)
    assert runner.calls[0][1:] == ("install", "--ignore-scripts", "--no-audit", "--no-fund")
    assert all("SECRET" not in env and "OPENAI_API_KEY" not in env for env in runner.envs)
    assert service.run_job(project.project_id, queued.job_id, actor="worker") == completed


def test_execution_failure_is_safe_and_budget_output_does_not_break_job(tmp_path):
    runner = FakeRunner(failure="build", output_bytes=999_999)
    service, project, generated = build_execution_service(tmp_path, runner=runner)
    queued = service.create_job(
        project_id=project.project_id,
        generation_job_id=generated.job_id,
        actor="user",
        reason="validate",
        budget=ExecutionBudget(max_output_bytes=1024),
    )
    failed = service.run_job(project.project_id, queued.job_id, actor="worker")
    assert failed.status in {"failed", "budget_exhausted"}
    assert failed.error_code == "output_limit" or failed.error_code == "command_failed"
    assert failed.error_summary is not None
    assert "999999" not in failed.error_summary
    assert failed.consumed_output_bytes <= failed.budget.max_output_bytes


def test_execution_rejects_tampered_workspace(tmp_path):
    service, project, generated = build_execution_service(tmp_path)
    workspace = service._workspace_path(
        service.create_job(project_id=project.project_id, generation_job_id=generated.job_id, actor="user", reason="validate")
    )
    (workspace / "package.json").write_text("{}", encoding="utf-8")
    job = service.list_jobs(project.project_id)[0]
    failed = service.run_job(project.project_id, job.job_id, actor="worker")
    assert failed.status == "failed"
    assert failed.error_code == "sandbox_violation"


def test_generation_template_contains_b4_validation_hooks(tmp_path):
    _, _, generation, project, _ = build_generation_services(tmp_path / "workspaces")
    job = generation.create_job(project_id=project.project_id, actor="user", reason="generate")
    contract = generation._contract_for(job)
    files = generation._render_files(contract)
    assert "preview" in files["package.json"]
    assert "@axe-core/playwright" in files["package.json"]
    assert "Show error" in files["src/App.tsx"]
    assert "AxeBuilder" in files["tests/generated-contract.spec.ts"]
    assert "screenshot" in files["tests/generated-contract.spec.ts"]
