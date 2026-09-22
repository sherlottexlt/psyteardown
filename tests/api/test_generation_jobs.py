from fastapi.testclient import TestClient

from psyteardown.api.app import create_app
from .test_proposal_jobs import _confirmed_intent
from .payloads import contract_proposal


def _confirmed_web_contract(client: TestClient) -> tuple[str, dict]:
    project_id, intent = _confirmed_intent(client)
    problem_job = client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs",
        json={"kind": "problem_model", "actor": "user-li", "reason": "generate"},
    ).json()
    client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs/{problem_job['job_id']}/runs",
        json={"actor": "local-worker"},
    )
    problem = client.get(f"/api/v1/projects/{project_id}").json()["problem_model"]
    confirmed_problem = client.post(
        f"/api/v1/projects/{project_id}/problem-model/{problem['problem_model_id']}/confirmations",
        json={"expected_revision": problem["meta"]["revision"], "actor": "user-li", "reason": "review"},
    ).json()
    contract = client.post(
        f"/api/v1/projects/{project_id}/outcome-contract/proposals",
        json={
            "proposal": contract_proposal(intent["revision_id"], confirmed_problem["revision_id"]),
            "actor": "studio", "reason": "define outcome",
        },
    ).json()
    client.post(
        f"/api/v1/projects/{project_id}/outcome-contract/{contract['outcome_contract_id']}/confirmations",
        json={"expected_revision": contract["meta"]["revision"], "actor": "user-li", "reason": "review boundary"},
    )
    thesis_job = client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs",
        json={"kind": "product_theses", "actor": "user-li", "reason": "search"},
    ).json()
    client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs/{thesis_job['job_id']}/runs",
        json={"actor": "local-worker"},
    )
    thesis = client.get(f"/api/v1/projects/{project_id}").json()["product_theses"][0]
    client.post(
        f"/api/v1/projects/{project_id}/product-theses/{thesis['thesis_id']}/transitions",
        json={
            "expected_revision": thesis["meta"]["revision"], "to_status": "exploring",
            "actor": "user-li", "actor_type": "human", "reason": "authorize exploration",
        },
    )
    web_proposal_job = client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs",
        json={"kind": "web_generation_contract", "actor": "user-li", "reason": "describe Web realization"},
    ).json()
    client.post(
        f"/api/v1/projects/{project_id}/proposal-jobs/{web_proposal_job['job_id']}/runs",
        json={"actor": "local-worker"},
    )
    draft = client.get(f"/api/v1/projects/{project_id}").json()["web_generation_contract"]
    confirmed = client.post(
        f"/api/v1/projects/{project_id}/web-generation-contract/{draft['web_generation_contract_id']}/confirmations",
        json={"expected_revision": draft["meta"]["revision"], "actor": "user-li", "reason": "confirm generation"},
    )
    assert confirmed.status_code == 201
    return project_id, confirmed.json()


def test_generation_job_api_is_idempotent_and_persists_workspace(tmp_path):
    database = tmp_path / "product-studio.sqlite3"
    with TestClient(create_app(database_path=database)) as client:
        project_id, contract = _confirmed_web_contract(client)
        queued = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs",
            json={"actor": "user-li", "reason": "materialize"},
        )
        assert queued.status_code == 202
        duplicate = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs",
            json={"actor": "user-li", "reason": "repeat click"},
        )
        assert duplicate.json()["job_id"] == queued.json()["job_id"]
        completed = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs/{queued.json()['job_id']}/runs",
            json={"actor": "local-worker"},
        )
        assert completed.status_code == 200
        payload = completed.json()
        assert payload["status"] == "succeeded"
        assert payload["web_generation_contract_revision_id"] == contract["revision_id"]
        assert payload["sandbox"]["network_policy"] == "none"
        assert payload["sandbox"]["execution_policy"] == "not_executed"
        assert payload["manifest"]["total_bytes"] == payload["consumed_bytes"]

    with TestClient(create_app(database_path=database)) as restarted:
        recovered = restarted.get(
            f"/api/v1/projects/{project_id}/generation-jobs/{queued.json()['job_id']}"
        )
        assert recovered.status_code == 200
        assert recovered.json()["status"] == "succeeded"


def test_generation_job_requires_confirmed_contract(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "product.sqlite3")) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "No contract", "actor": "user-li", "reason": "start", "created_from": []},
        ).json()
        response = client.post(
            f"/api/v1/projects/{project['project_id']}/generation-jobs",
            json={"actor": "user-li", "reason": "materialize"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "domain_gate"
