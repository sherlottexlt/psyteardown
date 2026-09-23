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


def test_safe_environment_keeps_windows_runtime_variables_case_insensitively(monkeypatch):
    # Windows exposes os.environ keys upper-cased (SYSTEMROOT); without it Node
    # cannot initialise its CSPRNG and every real execution step crashes.
    from psyteardown.product.execution import _safe_environment

    monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\system32\cmd.exe")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    env = {key.upper(): value for key, value in _safe_environment().items()}
    assert env["SYSTEMROOT"] == r"C:\Windows"
    assert env["COMSPEC"] == r"C:\Windows\system32\cmd.exe"
    assert "OPENAI_API_KEY" not in env


def test_safe_environment_uses_distinct_empty_npm_configs_outside_workspace(tmp_path):
    # npm refuses to load one path as both user and global config, which made
    # the previous shared NUL / /dev/null setting fail every real install.
    from pathlib import Path

    from psyteardown.product.execution import _safe_environment

    env = _safe_environment()
    user, global_ = Path(env["NPM_CONFIG_USERCONFIG"]), Path(env["NPM_CONFIG_GLOBALCONFIG"])
    assert user.is_absolute() and global_.is_absolute()
    assert user.resolve() != global_.resolve()
    assert user.read_text(encoding="utf-8") == "" and global_.read_text(encoding="utf-8") == ""


def _port_open(port: int) -> bool:
    import socket

    with socket.socket() as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def test_preview_process_tree_is_stopped_after_browser_step(tmp_path):
    # Mirrors npm.cmd -> node vite: killing only the wrapper orphaned the
    # server, and the next execution then validated a stale workspace.
    import subprocess
    import sys
    import time

    from psyteardown.product.execution import SubprocessExecutionCommandRunner

    if _port_open(4173):
        pytest.skip("preview port 4173 is already in use on this host")
    wrapper = (
        "import subprocess, sys; "
        "subprocess.Popen([sys.executable, '-m', 'http.server', '4173', '--bind', '127.0.0.1'], "
        "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).wait()"
    )
    runner = SubprocessExecutionCommandRunner()
    preview, browser = runner.run_preview_and_browser(
        preview_argv=[sys.executable, "-c", wrapper],
        browser_argv=[sys.executable, "-c", "pass"],
        cwd=tmp_path,
        timeout=30,
        env=dict(__import__("os").environ),
    )
    assert preview.exit_code == 0 and browser.exit_code == 0
    deadline = time.monotonic() + 5
    while _port_open(4173) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not _port_open(4173), "preview server outlived its execution step"


def test_preview_refuses_to_validate_an_already_bound_port(tmp_path):
    import socket
    import sys

    from psyteardown.product.execution import ExecutionCommandError, SubprocessExecutionCommandRunner

    if _port_open(4173):
        pytest.skip("preview port 4173 is already in use on this host")
    with socket.socket() as squatter:
        squatter.bind(("127.0.0.1", 4173))
        squatter.listen()
        with pytest.raises(ExecutionCommandError) as error:
            SubprocessExecutionCommandRunner().run_preview_and_browser(
                preview_argv=[sys.executable, "-c", "pass"],
                browser_argv=[sys.executable, "-c", "pass"],
                cwd=tmp_path,
                timeout=10,
                env=dict(__import__("os").environ),
            )
    assert error.value.code == "preview_port_busy"


def test_workspace_validation_tolerates_real_build_byproducts(tmp_path):
    # A real `tsc -b && vite build` writes tsconfig.tsbuildinfo, and npm links
    # node_modules/.bin on POSIX; neither is generated source, so later
    # consumers (retry, B5 repair, B6 export) must still accept the workspace.
    from psyteardown.product.execution import validate_generated_workspace

    service, project, generated = build_execution_service(tmp_path)
    workspace = tmp_path / "workspaces" / generated.workspace_relative_path
    (workspace / "tsconfig.tsbuildinfo").write_text("{}", encoding="utf-8")
    (workspace / "node_modules" / ".bin").mkdir(parents=True)
    try:
        (workspace / "node_modules" / ".bin" / "vite").symlink_to(workspace / "package.json")
    except OSError:
        pass
    validate_generated_workspace(workspace, generated)

    (workspace / "src" / "extra.ts").write_text("export {};\n", encoding="utf-8")
    with pytest.raises(Exception, match="integrity"):
        validate_generated_workspace(workspace, generated)
