"""Bounded, local-first Web source generation for the Product Studio slice."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from psyteardown.experience.models import DependencyRef, DomainStateError, RevisionMeta
from psyteardown.product.models import (
    GENERATION_DEFAULT_MAX_COST_UNITS,
    GENERATION_DEFAULT_MAX_DURATION_SECONDS,
    GENERATION_MODEL_PROVIDER,
    GENERATION_MODEL_VERSION,
    GenerationBudget,
    GenerationManifest,
    GeneratedFile,
    ModelCallRecord,
    ProductGenerationJob,
    model_generation_budget,
    WebProductGenerationContract,
    WEB_OUTPUT_PATHS,
    WEB_TEMPLATE_ID,
    WEB_TEMPLATE_VERSION,
)
from psyteardown.product.repositories import ProductRepositoryError
from psyteardown.product.source_model import (
    SOURCE_MODEL_SYSTEM,
    ProductSourceModel,
    SourceModelError,
    build_source_prompt,
    check_model_source,
    contract_browser_test,
    parse_source_reply,
    timed_generate,
)


class ProductGenerationJobRepository(Protocol):
    def save_generation_job(
        self, job: ProductGenerationJob, *, expected_revision: int | None
    ) -> ProductGenerationJob: ...

    def get_generation_job(self, job_id: str) -> ProductGenerationJob | None: ...

    def list_generation_jobs(
        self, *, project_id: str | None = None
    ) -> list[ProductGenerationJob]: ...

    def get_current(self, object_type: str, object_id: str): ...

    def get_revision(self, object_type: str, revision_id: str): ...


class InMemoryProductGenerationJobRepository:
    """Revisioned in-memory adapter used by generation tests."""

    def __init__(self) -> None:
        self._revisions: dict[str, dict[int, ProductGenerationJob]] = defaultdict(dict)
        self._current: dict[str, int] = {}
        self._objects: dict[tuple[str, str], object] = {}

    def attach_product_repository(self, repository: object) -> None:
        self._product_repository = repository

    def save_generation_job(
        self, job: ProductGenerationJob, *, expected_revision: int | None
    ) -> ProductGenerationJob:
        current = self.get_generation_job(job.job_id)
        _validate_generation_job_revision(current, job, expected_revision)
        self._revisions[job.job_id][job.meta.revision] = job
        self._current[job.job_id] = job.meta.revision
        return job

    def get_generation_job(self, job_id: str) -> ProductGenerationJob | None:
        revision = self._current.get(job_id)
        return self._revisions[job_id].get(revision) if revision else None

    def list_generation_jobs(
        self, *, project_id: str | None = None
    ) -> list[ProductGenerationJob]:
        values = [self.get_generation_job(job_id) for job_id in self._current]
        return sorted(
            [
                value
                for value in values
                if value is not None
                and (project_id is None or value.project_id == project_id)
            ],
            key=lambda item: (item.meta.created_at, item.job_id),
        )

    def get_current(self, object_type: str, object_id: str):
        repository = getattr(self, "_product_repository", None)
        if repository is None:
            return None
        return repository.get_current(object_type, object_id)

    def get_revision(self, object_type: str, revision_id: str):
        repository = getattr(self, "_product_repository", None)
        if repository is None:
            return None
        return repository.get_revision(object_type, revision_id)


class _BudgetExceeded(RuntimeError):
    pass


class _SandboxViolation(RuntimeError):
    pass


class _StaleInput(RuntimeError):
    pass


class _ModelAttemptFailed(RuntimeError):
    def __init__(self, record: ModelCallRecord, error_code: str, error_summary: str) -> None:
        super().__init__(error_summary)
        self.record = record
        self.error_code = error_code
        self.error_summary = error_summary


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_FORBIDDEN_NAMES = {".env", ".git", "id_rsa", "id_ed25519", "credentials.json"}


class ProductGenerationJobService:
    """Materialize a confirmed B2 contract without executing generated code."""

    def __init__(
        self,
        application,
        job_repository: ProductGenerationJobRepository,
        *,
        workspace_root: Path | str = Path("output/product-studio/workspaces"),
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[str], str] | None = None,
        source_model: ProductSourceModel | None = None,
        transcript_root: Path | str | None = None,
    ) -> None:
        self.application = application
        self.source_model = source_model
        self.job_repository = job_repository
        if hasattr(job_repository, "attach_product_repository"):
            job_repository.attach_product_repository(application.repository)
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self._root = self.workspace_root.resolve()
        # Model transcripts live beside, never inside, job workspaces so they
        # are not part of the manifest or of any delivery bundle.
        self.transcript_root = Path(transcript_root) if transcript_root else self.workspace_root.parent / "model-calls"
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda prefix: f"{prefix}-{uuid4().hex}")

    def create_job(
        self,
        *,
        project_id: str,
        actor: str,
        reason: str,
        budget: GenerationBudget | None = None,
        source: Literal["template", "model"] = "template",
    ) -> ProductGenerationJob:
        view = self.application.get_project_view(project_id)
        if view.project.status != "active":
            raise DomainStateError("product project must be active for generation jobs")
        contract = view.web_generation_contract
        if contract is None or contract.status != "confirmed":
            raise DomainStateError(
                "a human-confirmed Web generation contract is required before source generation"
            )
        if source == "model":
            if self.source_model is None:
                raise DomainStateError("model source generation requires a configured source model provider")
            selected_budget = budget or model_generation_budget()
        else:
            selected_budget = budget or GenerationBudget()
            if (
                selected_budget.max_cost_units > GENERATION_DEFAULT_MAX_COST_UNITS
                or selected_budget.max_duration_seconds > GENERATION_DEFAULT_MAX_DURATION_SECONDS
            ):
                raise DomainStateError("template generation budget exceeds the template limits")
        dependency = DependencyRef(
            object_type="web_generation_contract",
            object_id=contract.web_generation_contract_id,
            revision=contract.meta.revision,
        )
        fingerprint = _fingerprint(project_id, dependency, selected_budget, source=source)
        # A model draft is non-deterministic and each explicit request spends
        # budget, so only an unfinished model job is reused.
        reusable_statuses = {"queued", "running", "paused"} if source == "model" else {"queued", "running", "paused", "succeeded"}
        reusable = next(
            (
                item
                for item in reversed(self.job_repository.list_generation_jobs(project_id=project_id))
                if item.fingerprint == fingerprint
                and item.status in reusable_statuses
            ),
            None,
        )
        if reusable:
            return reusable
        job_id = self._id("generation-job")
        workspace_path = f"{_safe_segment(project_id)}/{_safe_segment(job_id)}"
        job = ProductGenerationJob(
            job_id=job_id,
            revision_id=f"{job_id}.r1",
            meta=RevisionMeta(
                revision=1,
                created_at=self._now(),
                created_by=actor,
                reason=reason,
            ),
            project_id=project_id,
            input_dependencies=(dependency,),
            web_generation_contract_revision_id=contract.revision_id,
            workspace_id=job_id,
            workspace_relative_path=workspace_path,
            budget=selected_budget,
            fingerprint=fingerprint,
            **(
                {"provider": GENERATION_MODEL_PROVIDER, "provider_version": GENERATION_MODEL_VERSION, "materialization_kind": "model"}
                if source == "model"
                else {}
            ),
        )
        return self.job_repository.save_generation_job(job, expected_revision=None)

    def get_job(self, project_id: str, job_id: str) -> ProductGenerationJob:
        job = self.job_repository.get_generation_job(job_id)
        if job is None:
            raise DomainStateError(f"unknown product generation job: {job_id}")
        if job.project_id != project_id:
            raise DomainStateError(
                f"product generation job belongs to project {job.project_id}, not {project_id}"
            )
        return job

    def list_jobs(self, project_id: str) -> tuple[ProductGenerationJob, ...]:
        self.application.get_project_view(project_id)
        return tuple(self.job_repository.list_generation_jobs(project_id=project_id))

    def run_job(self, project_id: str, job_id: str, *, actor: str) -> ProductGenerationJob:
        job = self.get_job(project_id, job_id)
        if job.status == "succeeded":
            return job
        if job.status == "paused":
            raise DomainStateError("paused generation job must be resumed before it can run")
        if job.status not in {"queued", "running"}:
            raise DomainStateError(f"product generation job cannot run from status {job.status}")
        reconciled = self._reconcile_workspace(job, actor=actor)
        if reconciled is not None:
            return reconciled
        if not self._inputs_are_current(job):
            return self._transition(
                job,
                status="stale_input",
                actor=actor,
                reason="confirmed generation input revision changed",
            )
        if job.attempt >= job.budget.max_attempts or job.consumed_cost_units >= job.budget.max_cost_units:
            return self._transition(
                job,
                status="budget_exhausted",
                actor=actor,
                reason="generation budget exhausted",
                error_code="budget_exhausted",
                error_summary="The generation budget was exhausted before another attempt.",
            )
        started = time.monotonic()
        running = self._transition(
            job,
            status="running",
            actor=actor,
            reason="generation worker claimed job",
            attempt=job.attempt + 1,
            checkpoint_step="prepare",
            consumed_cost_units=job.consumed_cost_units + 1,
        )
        try:
            contract = self._contract_for(running)
            running = self._transition(
                running,
                status="running",
                actor=actor,
                reason="generation inputs prepared",
                checkpoint_step="generate",
            )
            files = self._render_files(contract)
            if running.materialization_kind == "model":
                files, record = self._model_files(running, contract, files)
                running = self._transition(
                    running,
                    status="running",
                    actor=actor,
                    reason="model source accepted by static gate",
                    checkpoint_step="generate",
                    model_calls=(*running.model_calls, record),
                )
            elapsed = time.monotonic() - started
            self._check_budget(running.budget, files, elapsed)
            if not self._inputs_are_current(running):
                raise _StaleInput("confirmed generation input revision changed")
            running = self._transition(
                running,
                status="running",
                actor=actor,
                reason="template files rendered",
                checkpoint_step="validate",
                consumed_files=len(files),
                consumed_bytes=sum(len(content.encode("utf-8")) for _, content in files.items()),
                consumed_duration_seconds=elapsed,
            )
            manifest = self._write_workspace(running, files)
            elapsed = time.monotonic() - started
            self._check_budget(running.budget, files, elapsed)
            if not self._inputs_are_current(running):
                workspace = self._workspace_path(running)
                if workspace.exists():
                    shutil.rmtree(workspace)
                raise _StaleInput("confirmed generation input revision changed")
        except _StaleInput:
            workspace = self._workspace_path(running)
            if workspace.exists():
                shutil.rmtree(workspace)
            return self._transition(
                running,
                status="stale_input",
                actor=actor,
                reason="confirmed generation input revision changed before commit",
                consumed_duration_seconds=time.monotonic() - started,
            )
        except _BudgetExceeded:
            workspace = self._workspace_path(running)
            if workspace.exists():
                shutil.rmtree(workspace)
            return self._transition(
                running,
                status="budget_exhausted",
                actor=actor,
                reason="generation exceeded its local budget",
                error_code="budget_exhausted",
                error_summary="The generated workspace exceeded the configured local budget.",
                consumed_duration_seconds=time.monotonic() - started,
            )
        except _ModelAttemptFailed as failure:
            return self._transition(
                running,
                status="failed",
                actor=actor,
                reason="model source attempt did not pass",
                error_code=failure.error_code,
                error_summary=failure.error_summary,
                model_calls=(*running.model_calls, failure.record),
                consumed_duration_seconds=time.monotonic() - started,
            )
        except _SandboxViolation:
            return self._transition(
                running,
                status="failed",
                actor=actor,
                reason="generation sandbox policy rejected output",
                error_code="sandbox_violation",
                error_summary="The generated workspace did not satisfy the local sandbox policy.",
                consumed_duration_seconds=time.monotonic() - started,
            )
        except ProductRepositoryError:
            raise
        except Exception:
            return self._transition(
                running,
                status="failed",
                actor=actor,
                reason="template generation failed",
                error_code="generation_failed",
                error_summary="The deterministic template could not be materialized.",
                consumed_duration_seconds=time.monotonic() - started,
            )
        return self._transition(
            running,
            status="succeeded",
            actor=actor,
            reason="model workspace materialized" if running.materialization_kind == "model" else "template workspace materialized",
            checkpoint_step="validate",
            consumed_duration_seconds=elapsed,
            manifest=manifest,
        )

    def pause_job(self, project_id: str, job_id: str, *, actor: str) -> ProductGenerationJob:
        job = self.get_job(project_id, job_id)
        if job.status not in {"queued", "running"}:
            raise DomainStateError("only queued or running generation jobs can be paused")
        return self._transition(job, status="paused", actor=actor, reason="generation paused by user")

    def resume_job(self, project_id: str, job_id: str, *, actor: str) -> ProductGenerationJob:
        job = self.get_job(project_id, job_id)
        if job.status != "paused":
            raise DomainStateError("only paused generation jobs can be resumed")
        if not self._inputs_are_current(job):
            return self._transition(job, status="stale_input", actor=actor, reason="confirmed generation input revision changed")
        return self._transition(job, status="queued", actor=actor, reason="generation resumed by user")

    def cancel_job(self, project_id: str, job_id: str, *, actor: str) -> ProductGenerationJob:
        job = self.get_job(project_id, job_id)
        if job.status not in {"queued", "running", "paused"}:
            raise DomainStateError("only active generation jobs can be cancelled")
        return self._transition(job, status="cancelled", actor=actor, reason="generation cancelled by user")

    def retry_job(self, project_id: str, job_id: str, *, actor: str) -> ProductGenerationJob:
        job = self.get_job(project_id, job_id)
        if job.status not in {"failed", "stale_input"}:
            raise DomainStateError("only failed or stale generation jobs can be retried")
        if not self._inputs_are_current(job):
            raise DomainStateError("generation job inputs are no longer current; create a new job")
        if job.attempt >= job.budget.max_attempts or job.consumed_cost_units >= job.budget.max_cost_units:
            return self._transition(
                job,
                status="budget_exhausted",
                actor=actor,
                reason="generation retry exceeds budget",
                error_code="budget_exhausted",
                error_summary="The generation retry budget was exhausted.",
            )
        return self._transition(job, status="queued", actor=actor, reason="generation retry requested")

    def _contract_for(self, job: ProductGenerationJob) -> WebProductGenerationContract:
        value = self.job_repository.get_revision(
            "web_generation_contract", job.web_generation_contract_revision_id
        )
        if not isinstance(value, WebProductGenerationContract):
            raise DomainStateError("pinned Web generation contract is unavailable")
        return value

    def _inputs_are_current(self, job: ProductGenerationJob) -> bool:
        dependency = job.input_dependencies[0]
        current = self.job_repository.get_current(dependency.object_type, dependency.object_id)
        if not (
            isinstance(current, WebProductGenerationContract)
            and current.meta.revision == dependency.revision
            and current.status == "confirmed"
        ):
            return False
        # A contract is itself pinned to thesis/outcome revisions.  Treat a
        # transitive upstream change as stale even when the contract aggregate
        # has not yet been amended, so a generation job cannot materialize an
        # obsolete realization after an upstream decision changes.
        for upstream in current.dependencies:
            upstream_current = self.job_repository.get_current(
                upstream.object_type, upstream.object_id
            )
            if upstream_current is None or upstream_current.meta.revision != upstream.revision:
                return False
            if upstream.object_type == "product_thesis":
                if getattr(upstream_current, "status", None) not in {"exploring", "selected"}:
                    return False
            elif getattr(upstream_current, "status", None) != "confirmed":
                return False
        return True

    def _render_files(self, contract: WebProductGenerationContract) -> dict[str, str]:
        if contract.template_id != WEB_TEMPLATE_ID or contract.template_version != WEB_TEMPLATE_VERSION:
            raise _SandboxViolation("unsupported template")
        if tuple(contract.output_paths) != WEB_OUTPUT_PATHS:
            raise _SandboxViolation("unsupported output layout")
        payload = {
            "app_title": contract.app_title,
            "screens": [item.model_dump(mode="json") for item in contract.screens],
            "tasks": [item.model_dump(mode="json") for item in contract.tasks],
            "states": [item.model_dump(mode="json") for item in contract.states],
            "content_slots": [item.model_dump(mode="json") for item in contract.content_slots],
        }
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        escaped_title = json.dumps(contract.app_title, ensure_ascii=False)
        app = (
            'import {useState} from "react";\n'
            'import "./styles.css";\n\n'
            f"const contract = {serialized} as const;\n\n"
            f"const appTitle = {escaped_title} as const;\n\n"
            "export default function App() {\n"
            "  const [state, setState] = useState<'ready' | 'success' | 'stopped' | 'error'>('ready');\n"
            "  return <main aria-labelledby=\"app-title\"><h1 id=\"app-title\">{appTitle}</h1>"
            "<p>{contract.content_slots[1]?.fallback_text ?? 'Choose a focus task and duration.'}</p>"
            "<p role=\"status\">{state === 'success' ? 'Local action confirmed.' : state === 'stopped' ? 'Session stopped.' : state === 'error' ? 'Something went wrong.' : 'Ready.'}</p>"
            "<button onClick={() => setState('success')}>Continue</button>"
            "<button onClick={() => setState('error')}>Show error</button>"
            "<button onClick={() => setState('stopped')}>Stop</button></main>;\n"
            "}\n"
        )
        fixture = json.dumps({"source": "local_fixture", "items": []}, ensure_ascii=False, indent=2) + "\n"
        package_json = json.dumps(
            {
                "private": True,
                "type": "module",
                "scripts": {"build": "tsc -b && vite build", "preview": "vite preview", "test:e2e": "playwright test"},
                "dependencies": {"react": "19.1.1", "react-dom": "19.1.1"},
                "devDependencies": {
                    "@playwright/test": "1.55.1",
                    "@axe-core/playwright": "4.13.0",
                    "@types/react": "19.1.16",
                    "@types/react-dom": "19.1.9",
                    "@vitejs/plugin-react": "5.0.4",
                    "@testing-library/react": "16.3.0",
                    "typescript": "5.9.3",
                    "vite": "7.1.9",
                    "vitest": "5.0.1",
                },
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        index_html = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"UTF-8\" /><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /><title>Product Studio output</title></head><body><div id=\"root\"></div><script type=\"module\" src=\"/src/main.tsx\"></script></body></html>\n"
        tsconfig = json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2022",
                    "useDefineForClassFields": True,
                    "lib": ["ES2022", "DOM", "DOM.Iterable"],
                    "allowJs": False,
                    "skipLibCheck": True,
                    "esModuleInterop": True,
                    "allowSyntheticDefaultImports": True,
                    "strict": True,
                    "forceConsistentCasingInFileNames": True,
                    "module": "ESNext",
                    "moduleResolution": "Bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "noEmit": True,
                    "jsx": "react-jsx",
                },
                "include": ["src"],
            },
            indent=2,
        ) + "\n"
        vite_config = "import {defineConfig} from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({plugins: [react()]});\n"
        playwright_config = (
            "import {defineConfig} from '@playwright/test';\n"
            "export default defineConfig({use: {baseURL: process.env.BASE_URL ?? 'http://127.0.0.1:4173'}, "
            "testDir: './tests', reporter: 'list'});\n"
        )
        test = (
            "import AxeBuilder from '@axe-core/playwright';\n"
            "import {expect, test} from '@playwright/test';\n"
            "test('generated contract covers startup, key task, stop/error states and accessibility', async ({page}) => {\n"
            "  await page.goto('/');\n"
            "  await expect(page.getByRole('heading')).toBeVisible();\n"
            "  await expect(page.getByRole('button', {name: 'Continue'})).toBeVisible();\n"
            "  await page.getByRole('button', {name: 'Continue'}).click();\n"
            "  await expect(page.getByRole('status')).toContainText('Local action confirmed.');\n"
            "  await page.getByRole('button', {name: 'Show error'}).click();\n"
            "  await expect(page.getByRole('status')).toContainText('Something went wrong.');\n"
            "  await page.getByRole('button', {name: 'Stop'}).click();\n"
            "  await expect(page.getByRole('status')).toContainText('Session stopped.');\n"
            "  const results = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa']).analyze();\n"
            "  expect(results.violations.filter((item) => item.impact === 'critical' || item.impact === 'serious')).toEqual([]);\n"
            "  await page.screenshot({path: 'test-results/generated-product.png', fullPage: true});\n"
            "});\n"
        )
        return {
            "package.json": package_json,
            "index.html": index_html,
            "tsconfig.json": tsconfig,
            "vite.config.ts": vite_config,
            "playwright.config.ts": playwright_config,
            "src/main.tsx": 'import {StrictMode} from "react";\nimport {createRoot} from "react-dom/client";\nimport App from "./App";\nimport "./styles.css";\n\ncreateRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);\n',
            "src/App.tsx": app,
            "src/styles.css": "body { font-family: system-ui, sans-serif; margin: 2rem; } button { margin-right: .5rem; }\n",
            "tests/generated-contract.spec.ts": test,
            "public/fixture.json": fixture,
        }

    def _model_files(
        self, job: ProductGenerationJob, contract: WebProductGenerationContract, template: dict[str, str]
    ) -> tuple[dict[str, str], ModelCallRecord]:
        """One model call: send only the contract, keep the transcript, gate the reply."""
        model = self.source_model
        if model is None:
            raise DomainStateError("model source generation requires a configured source model provider")
        attempt = len(job.model_calls) + 1
        previous = job.model_calls[-1].rejection_reasons if job.model_calls else ()
        prompt = build_source_prompt(contract, previous)
        request_sha = hashlib.sha256(f"{SOURCE_MODEL_SYSTEM}\n\n{prompt}".encode("utf-8")).hexdigest()
        relative = "/".join((_safe_segment(job.project_id), _safe_segment(job.job_id), f"attempt-{attempt}.json"))
        transcript = {
            "job_id": job.job_id,
            "attempt": attempt,
            "provider": model.name,
            "model": model.model,
            "sent_object_types": ["web_generation_contract"],
            "web_generation_contract_revision_id": contract.revision_id,
            "system": SOURCE_MODEL_SYSTEM,
            "prompt": prompt,
        }
        base = {
            "attempt": attempt,
            "provider": model.name,
            "request_sha256": request_sha,
            "transcript_path": relative,
        }
        started = time.monotonic()
        try:
            reply, duration = timed_generate(model, system=SOURCE_MODEL_SYSTEM, prompt=prompt)
        except SourceModelError as exc:
            transcript["error"] = str(exc)
            self._write_transcript(relative, transcript)
            record = ModelCallRecord(**base, model=model.model, outcome="failed", duration_seconds=time.monotonic() - started)
            raise _ModelAttemptFailed(record, "model_call_failed", f"The model call failed: {exc}.") from exc
        response_sha = hashlib.sha256(reply.text.encode("utf-8")).hexdigest()
        transcript.update(
            response=reply.text,
            response_model=reply.model,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            truncated=reply.truncated,
        )
        files, reasons = parse_source_reply(reply.text, truncated=reply.truncated)
        if not reasons:
            reasons = check_model_source(files, contract)
        transcript["gate"] = {"accepted": not reasons, "reasons": reasons}
        self._write_transcript(relative, transcript)
        record = ModelCallRecord(
            **base,
            model=reply.model or model.model,
            outcome="rejected" if reasons else "accepted",
            response_sha256=response_sha,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            duration_seconds=duration,
            rejection_reasons=tuple(reason[:200] for reason in reasons),
        )
        if reasons:
            summary = f"The model draft was rejected by the static gate ({len(reasons)} issue(s)): {reasons[0]}."
            raise _ModelAttemptFailed(record, "model_output_rejected", summary[:240])
        merged = dict(template)
        merged.update(files)
        # The model never writes its own checks: B4 runs a contract-derived test.
        merged["tests/generated-contract.spec.ts"] = contract_browser_test(contract)
        return merged, record

    def _write_transcript(self, relative: str, payload: dict) -> None:
        target = self.transcript_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def transcript_path(self, job: ProductGenerationJob, attempt: int) -> Path:
        record = next((item for item in job.model_calls if item.attempt == attempt), None)
        if record is None:
            raise DomainStateError(f"unknown model call attempt: {attempt}")
        return self.transcript_root / record.transcript_path

    def _write_workspace(self, job: ProductGenerationJob, files: dict[str, str]) -> GenerationManifest:
        final = self._workspace_path(job)
        if final.exists():
            existing = self._read_manifest(final)
            if existing is not None:
                return existing
            raise _SandboxViolation("workspace already exists without a valid manifest")
        final.parent.mkdir(parents=True, exist_ok=True)
        if any(parent.is_symlink() for parent in (final.parent, self._root)):
            raise _SandboxViolation("workspace path contains a symlink")
        temporary = Path(tempfile.mkdtemp(prefix=f".{_safe_segment(job.job_id)}-", dir=self._root))
        try:
            for relative, content in files.items():
                self._validate_relative_path(relative)
                target = temporary / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            generated = tuple(
                GeneratedFile(
                    path=relative,
                    byte_count=len(content.encode("utf-8")),
                    sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                )
                for relative, content in sorted(files.items())
            )
            manifest = GenerationManifest(
                files=generated,
                total_bytes=sum(item.byte_count for item in generated),
            )
            (temporary / "generation-manifest.json").write_text(
                manifest.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
            )
            temporary.rename(final)
            return manifest
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise

    def _read_manifest(self, workspace: Path) -> GenerationManifest | None:
        path = workspace / "generation-manifest.json"
        try:
            if not path.is_file() or path.is_symlink():
                return None
            manifest = GenerationManifest.model_validate_json(path.read_text(encoding="utf-8"))
            self._assert_contained(workspace.resolve())
            for item in manifest.files:
                self._validate_relative_path(item.path)
                target = (workspace / item.path).resolve(strict=False)
                self._assert_contained(target)
                if not target.is_file() or target.is_symlink():
                    return None
                payload = target.read_bytes()
                if len(payload) != item.byte_count:
                    return None
                if hashlib.sha256(payload).hexdigest() != item.sha256:
                    return None
            return manifest
        except Exception:
            return None

    def _reconcile_workspace(self, job: ProductGenerationJob, *, actor: str) -> ProductGenerationJob | None:
        manifest = self._read_manifest(self._workspace_path(job))
        if manifest is None:
            return None
        if not self._inputs_are_current(job):
            return self._transition(job, status="stale_input", actor=actor, reason="confirmed generation input revision changed")
        return self._transition(
            job,
            status="succeeded",
            actor=actor,
            reason="reconciled previously materialized workspace",
            checkpoint_step="validate",
            manifest=manifest,
            consumed_files=len(manifest.files),
            consumed_bytes=manifest.total_bytes,
        )

    def _workspace_path(self, job: ProductGenerationJob) -> Path:
        candidate = (self._root / job.workspace_relative_path).resolve(strict=False)
        self._assert_contained(candidate)
        return candidate

    def _validate_relative_path(self, relative: str) -> None:
        path = relative.replace("\\", "/")
        if path.startswith("/") or ".." in path.split("/") or any(part in _FORBIDDEN_NAMES for part in path.split("/")):
            raise _SandboxViolation("generated path is not allowed")
        if not path or path.endswith("/"):
            raise _SandboxViolation("generated path is empty")

    def _assert_contained(self, candidate: Path) -> None:
        try:
            common = os.path.commonpath((str(self._root), str(candidate)))
        except ValueError as exc:
            raise _SandboxViolation("workspace path is outside the configured root") from exc
        if common != str(self._root):
            raise _SandboxViolation("workspace path is outside the configured root")

    def _check_budget(self, budget: GenerationBudget, files: dict[str, str], elapsed: float) -> None:
        total = sum(len(content.encode("utf-8")) for content in files.values())
        if len(files) > budget.max_files or total > budget.max_bytes or elapsed > budget.max_duration_seconds:
            raise _BudgetExceeded("generation budget exceeded")

    def _transition(self, current: ProductGenerationJob, *, status: str, actor: str, reason: str, **updates) -> ProductGenerationJob:
        revision = current.meta.revision + 1
        updated = current.model_copy(
            update={
                **updates,
                "revision_id": f"{current.job_id}.r{revision}",
                "meta": RevisionMeta(
                    revision=revision,
                    parent_revision_id=current.revision_id,
                    created_at=self._now(),
                    created_by=actor,
                    reason=reason,
                ),
                "status": status,
                "error_code": updates.get("error_code", None),
                "error_summary": updates.get("error_summary", None),
            }
        )
        return self.job_repository.save_generation_job(updated, expected_revision=current.meta.revision)

    def _id(self, prefix: str) -> str:
        value = self._id_factory(prefix)
        if not value:
            raise ValueError("id_factory returned an empty identifier")
        return value

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ProductGenerationJobService clock must be timezone-aware")
        return value


def _safe_segment(value: str) -> str:
    if _SAFE_SEGMENT.fullmatch(value):
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"id-{digest}"


def _fingerprint(project_id: str, dependency: DependencyRef, budget: GenerationBudget, *, source: str = "template") -> str:
    payload = {
        "project_id": project_id,
        "dependency": dependency.model_dump(mode="json"),
        "budget": budget.model_dump(mode="json"),
        "provider": GENERATION_MODEL_PROVIDER if source == "model" else "deterministic_template",
        "version": GENERATION_MODEL_VERSION if source == "model" else "b3-v1",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate_generation_job_revision(
    current: ProductGenerationJob | None,
    value: ProductGenerationJob,
    expected_revision: int | None,
) -> None:
    if current is None:
        if expected_revision is not None or value.meta.revision != 1:
            raise ProductRepositoryError("generation job first revision conflict")
        return
    if expected_revision != current.meta.revision:
        raise ProductRepositoryError(
            f"revision conflict: expected {expected_revision}, current {current.meta.revision}"
        )
    if value.meta.revision != current.meta.revision + 1:
        raise ProductRepositoryError("generation job revisions must increase by one")
    if value.meta.parent_revision_id != current.revision_id:
        raise ProductRepositoryError("generation job revision must reference current parent")
