import hashlib
import io
import zipfile

from fastapi.testclient import TestClient

from psyteardown.api.app import create_app
from tests.product.test_delivery import ArtifactRunner
from .test_generation_jobs import _confirmed_web_contract


def _verified_execution(client: TestClient) -> tuple[str, dict]:
    project_id, _ = _confirmed_web_contract(client)
    generation = client.post(
        f"/api/v1/projects/{project_id}/generation-jobs",
        json={"actor": "user-li", "reason": "materialize"},
    ).json()
    client.post(
        f"/api/v1/projects/{project_id}/generation-jobs/{generation['job_id']}/runs",
        json={"actor": "local-worker"},
    )
    # Only the subprocess boundary is faked; every HTTP/domain/persistence step is real.
    client.app.state.product_execution_job_service.runner = ArtifactRunner()
    execution = client.post(
        f"/api/v1/projects/{project_id}/execution-jobs",
        json={"generation_job_id": generation["job_id"], "actor": "user-li", "reason": "validate"},
    ).json()
    executed = client.post(
        f"/api/v1/projects/{project_id}/execution-jobs/{execution['job_id']}/runs",
        json={"actor": "local-worker"},
    ).json()
    assert executed["status"] == "succeeded"
    return project_id, executed


def test_delivery_bundle_api_exports_downloads_and_recovers(tmp_path):
    database = tmp_path / "product.sqlite3"
    with TestClient(create_app(database_path=database)) as client:
        project_id, executed = _verified_execution(client)
        created = client.post(
            f"/api/v1/projects/{project_id}/delivery-bundles",
            json={"execution_job_id": executed["job_id"], "actor": "user-li", "reason": "deliver"},
        )
        assert created.status_code == 201
        bundle = created.json()
        assert bundle["execution_job_revision_id"] == executed["revision_id"]
        assert bundle["outcome_evidence_level"] == "none"
        assert bundle["unverified_claims"]

        repeated = client.post(
            f"/api/v1/projects/{project_id}/delivery-bundles",
            json={"execution_job_id": executed["job_id"], "actor": "user-li", "reason": "repeat click"},
        )
        assert repeated.json()["bundle_id"] == bundle["bundle_id"]

        download = client.get(f"/api/v1/projects/{project_id}/delivery-bundles/{bundle['bundle_id']}/archive")
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"
        assert download.headers["x-content-sha256"] == bundle["archive_sha256"]
        assert hashlib.sha256(download.content).hexdigest() == bundle["archive_sha256"]
        with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
            assert "DELIVERY.md" in archive.namelist()

    with TestClient(create_app(database_path=database)) as restarted:
        listed = restarted.get(f"/api/v1/projects/{project_id}/delivery-bundles")
        assert [item["bundle_id"] for item in listed.json()] == [bundle["bundle_id"]]
        recovered = restarted.get(f"/api/v1/projects/{project_id}/delivery-bundles/{bundle['bundle_id']}/archive")
        assert hashlib.sha256(recovered.content).hexdigest() == bundle["archive_sha256"]


def test_delivery_bundle_api_gates_unverified_execution_and_tampering(tmp_path):
    database = tmp_path / "product.sqlite3"
    with TestClient(create_app(database_path=database)) as client:
        project_id, _ = _confirmed_web_contract(client)
        generation = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs",
            json={"actor": "user-li", "reason": "materialize"},
        ).json()
        client.post(
            f"/api/v1/projects/{project_id}/generation-jobs/{generation['job_id']}/runs",
            json={"actor": "local-worker"},
        )
        queued = client.post(
            f"/api/v1/projects/{project_id}/execution-jobs",
            json={"generation_job_id": generation["job_id"], "actor": "user-li", "reason": "validate"},
        ).json()
        rejected = client.post(
            f"/api/v1/projects/{project_id}/delivery-bundles",
            json={"execution_job_id": queued["job_id"], "actor": "user-li", "reason": "deliver"},
        )
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "domain_gate"
        assert "\\" not in rejected.json()["error"]["message"]

        missing = client.get(f"/api/v1/projects/{project_id}/delivery-bundles/delivery-bundle-missing")
        assert missing.status_code == 404

    with TestClient(create_app(database_path=database)) as client:
        project_id, executed = _verified_execution(client)
        bundle = client.post(
            f"/api/v1/projects/{project_id}/delivery-bundles",
            json={"execution_job_id": executed["job_id"], "actor": "user-li", "reason": "deliver"},
        ).json()
        archive = tmp_path / "exports" / f"{bundle['archive_sha256']}.zip"
        archive.write_bytes(b"not the delivered bytes")
        tampered = client.get(f"/api/v1/projects/{project_id}/delivery-bundles/{bundle['bundle_id']}/archive")
        assert tampered.status_code == 409
        assert tampered.json()["error"]["code"] == "invalid_state"
