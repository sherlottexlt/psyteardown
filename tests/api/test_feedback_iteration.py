from fastapi.testclient import TestClient

from psyteardown.api.app import create_app
from psyteardown.product.models import WebProductGenerationContract
from tests.product.test_delivery import ArtifactRunner
from tests.product.source_model_fixtures import ScriptedSourceModel, reference_app, reply_for
from .test_preview_feedback import _bundle, _feedback_body


def _run(client: TestClient, url: str) -> dict:
    response = client.post(url, json={"actor": "local-worker"})
    assert response.status_code == 200, response.json()
    return response.json()


def _submit_feedback(client: TestClient, project_id: str, bundle: dict, contract: dict) -> dict:
    created = client.post(
        f"/api/v1/projects/{project_id}/delivery-bundles/{bundle['bundle_id']}/feedback",
        json=_feedback_body(contract),
    )
    assert created.status_code == 201
    return created.json()


def _iteration_job(client: TestClient, project_id: str, feedback_id: str):
    return client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs",
        json={
            "kind": "web_generation_contract",
            "feedback_id": feedback_id,
            "actor": "user-li",
            "reason": "iterate from preview feedback",
        },
    )


def test_feedback_drives_a_confirmed_revision_through_delivery_and_diff(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "product.sqlite3")) as client:
        project_id, bundle, contract = _bundle(client)
        feedback = _submit_feedback(client, project_id, bundle, contract)
        assert feedback["disposition"] == "pending"

        created = _iteration_job(client, project_id, feedback["feedback_id"])
        assert created.status_code == 202
        job = created.json()
        assert job["feedback_id"] == feedback["feedback_id"]
        assert {item["object_type"] for item in job["input_dependencies"]} == {
            "web_generation_contract",
            "preview_feedback",
        }
        assert _iteration_job(client, project_id, feedback["feedback_id"]).json()["job_id"] == job["job_id"]

        ran = _run(client, f"/api/v1/projects/{project_id}/proposal-jobs/{job['job_id']}/runs")
        assert ran["status"] == "succeeded"
        proposed = client.get(f"/api/v1/projects/{project_id}").json()["web_generation_contract"]
        assert proposed["status"] == "proposed"
        assert proposed["web_generation_contract_id"] == contract["web_generation_contract_id"]
        assert proposed["meta"]["revision"] == contract["meta"]["revision"] + 1
        # Anchors stay valid and the report text never enters the contract.
        assert [item["screen_id"] for item in proposed["screens"]] == [item["screen_id"] for item in contract["screens"]]
        assert feedback["text"] not in str(proposed)
        assert any(item["source_type"] == "preview_feedback" for item in proposed["source_refs"])
        added = [item for item in proposed["acceptance_checks"] if item not in contract["acceptance_checks"]]
        assert len(added) == 1 and feedback["feedback_id"] in added[0]["assertion"]
        # Creating and running the job does not decide anything about the feedback.
        listed = client.get(f"/api/v1/projects/{project_id}/preview-feedback").json()
        assert listed[0]["status"] == "submitted" and listed[0]["disposition"] == "pending"

        confirmed = client.post(
            f"/api/v1/projects/{project_id}/web-generation-contract/"
            f"{proposed['web_generation_contract_id']}/confirmations",
            json={"expected_revision": proposed["meta"]["revision"], "actor": "user-li", "reason": "review"},
        )
        assert confirmed.status_code == 201, confirmed.json()

        generation = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs",
            json={"actor": "user-li", "reason": "materialize revision"},
        ).json()
        _run(client, f"/api/v1/projects/{project_id}/generation-jobs/{generation['job_id']}/runs")
        client.app.state.product_execution_job_service.runner = ArtifactRunner()
        execution = client.post(
            f"/api/v1/projects/{project_id}/execution-jobs",
            json={"generation_job_id": generation["job_id"], "actor": "user-li", "reason": "validate"},
        ).json()
        executed = _run(client, f"/api/v1/projects/{project_id}/execution-jobs/{execution['job_id']}/runs")
        assert executed["status"] == "succeeded"
        second = client.post(
            f"/api/v1/projects/{project_id}/delivery-bundles",
            json={"execution_job_id": executed["job_id"], "actor": "user-li", "reason": "deliver revision"},
        ).json()

        diff = client.get(
            f"/api/v1/projects/{project_id}/delivery-bundles/{second['bundle_id']}/diff",
            params={"base_bundle_id": bundle["bundle_id"]},
        )
        assert diff.status_code == 200
        body = diff.json()
        assert body["base_contract_revision_id"] == contract["revision_id"]
        assert body["target_contract_revision_id"] == confirmed.json()["revision_id"]
        assert body["contract_changes"] == [f"acceptance_checks: added {added[0]['check_id']}"]
        changes = {item["path"]: item["change"] for item in body["files"]}
        assert set(changes.values()) <= {"added", "removed", "modified", "unchanged"}
        assert changes["bundle-manifest.json"] == "modified"
        # The deterministic template does not consume acceptance checks, so a
        # revised contract yields identical source/build; the diff must say so.
        assert all(
            change == "unchanged"
            for path, change in changes.items()
            if path.startswith(("source/", "build/"))
        )

        decided = client.post(
            f"/api/v1/projects/{project_id}/preview-feedback/{feedback['feedback_id']}/disposition",
            json={
                "disposition": "incorporated",
                "expected_revision": 1,
                "actor": "user-li",
                "reason": "addressed by the confirmed revision",
            },
        )
        assert decided.status_code == 200
        assert decided.json()["disposition"] == "incorporated"
        assert decided.json()["text"] == feedback["text"]

        withdrawn = client.post(
            f"/api/v1/projects/{project_id}/preview-feedback/{feedback['feedback_id']}/withdrawal",
            json={"actor": "local-user", "expected_revision": 2},
        ).json()
        assert withdrawn["status"] == "withdrawn" and withdrawn["text"] is None
        assert withdrawn["disposition"] == "pending"


def test_iteration_gates_withdrawn_feedback_and_other_kinds(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "product.sqlite3")) as client:
        project_id, bundle, contract = _bundle(client)
        feedback = _submit_feedback(client, project_id, bundle, contract)

        wrong_kind = client.post(
            f"/api/v1/projects/{project_id}/proposal-jobs",
            json={"kind": "product_theses", "feedback_id": feedback["feedback_id"], "actor": "u", "reason": "r"},
        )
        assert wrong_kind.status_code == 409
        assert _iteration_job(client, project_id, "preview-feedback-unknown").status_code == 404

        job = _iteration_job(client, project_id, feedback["feedback_id"]).json()
        client.post(
            f"/api/v1/projects/{project_id}/preview-feedback/{feedback['feedback_id']}/withdrawal",
            json={"actor": "local-user", "expected_revision": 1},
        )
        stale = _run(client, f"/api/v1/projects/{project_id}/proposal-jobs/{job['job_id']}/runs")
        assert stale["status"] == "stale_input"
        current = client.get(f"/api/v1/projects/{project_id}").json()["web_generation_contract"]
        assert current["revision_id"] == contract["revision_id"]
        assert _iteration_job(client, project_id, feedback["feedback_id"]).status_code == 409
