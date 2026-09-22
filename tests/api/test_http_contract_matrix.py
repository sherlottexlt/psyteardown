from fastapi.testclient import TestClient

from psyteardown.api.app import create_app
from .payloads import (
    contract_proposal,
    intent_proposal,
    problem_proposal,
    thesis_proposal,
)


def _create_project(client: TestClient, name: str = "Focus boundary") -> str:
    response = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "collaboration_mode": "managed",
            "actor": "user-li",
            "reason": "start project",
            "created_from": [],
        },
    )
    assert response.status_code == 201
    return response.json()["project_id"]


def _confirm(
    client: TestClient,
    *,
    project_id: str,
    resource: str,
    object_id: str,
    revision: int = 1,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/{resource}/{object_id}/confirmations",
        json={
            "expected_revision": revision,
            "actor": "user-li",
            "reason": "reviewed and confirmed",
        },
    )
    assert response.status_code == 201
    return response.json()


def _bootstrap_complete_project(client: TestClient) -> tuple[str, dict]:
    project_id = _create_project(client)
    intent_response = client.post(
        f"/api/v1/projects/{project_id}/product-intent/proposals",
        json={
            "proposal": intent_proposal(),
            "actor": "studio",
            "reason": "structure user input",
        },
    )
    assert intent_response.status_code == 201
    intent_draft = intent_response.json()
    intent = _confirm(
        client,
        project_id=project_id,
        resource="product-intent",
        object_id=intent_draft["intent_id"],
    )

    problem_response = client.post(
        f"/api/v1/projects/{project_id}/problem-model/proposals",
        json={
            "proposal": problem_proposal(intent["revision_id"]),
            "actor": "studio",
            "reason": "compare explanations",
        },
    )
    assert problem_response.status_code == 201
    problem_draft = problem_response.json()
    problem = _confirm(
        client,
        project_id=project_id,
        resource="problem-model",
        object_id=problem_draft["problem_model_id"],
    )

    contract_response = client.post(
        f"/api/v1/projects/{project_id}/outcome-contract/proposals",
        json={
            "proposal": contract_proposal(
                intent["revision_id"], problem["revision_id"]
            ),
            "actor": "studio",
            "reason": "propose outcome boundary",
        },
    )
    assert contract_response.status_code == 201
    contract_draft = contract_response.json()
    contract = _confirm(
        client,
        project_id=project_id,
        resource="outcome-contract",
        object_id=contract_draft["outcome_contract_id"],
    )

    thesis_response = client.post(
        f"/api/v1/projects/{project_id}/product-theses/proposals",
        json={
            "proposal": thesis_proposal(
                problem["revision_id"], contract["revision_id"]
            ),
            "actor": "studio",
            "reason": "propose product path",
        },
    )
    assert thesis_response.status_code == 201
    thesis = thesis_response.json()
    transition_response = client.post(
        f"/api/v1/projects/{project_id}/product-theses/{thesis['thesis_id']}/transitions",
        json={
            "expected_revision": 1,
            "to_status": "selected",
            "actor": "user-li",
            "actor_type": "human",
            "reason": "select for low-cost prototyping",
            "authorization_ref": None,
        },
    )
    assert transition_response.status_code == 201
    return project_id, transition_response.json()


def test_complete_http_command_chain_and_sqlite_restart(tmp_path):
    database = tmp_path / "product-studio.sqlite3"
    with TestClient(create_app(database_path=database)) as first_client:
        project_id, selected = _bootstrap_complete_project(first_client)
        assert selected["status"] == "selected"
        assert selected["meta"]["revision"] == 2

        stale_response = first_client.post(
            f"/api/v1/projects/{project_id}/product-theses/{selected['thesis_id']}/transitions",
            headers={"X-Request-ID": "stale-thesis-transition"},
            json={
                "expected_revision": 1,
                "to_status": "rejected",
                "actor": "user-li",
                "actor_type": "human",
                "reason": "stale decision",
                "authorization_ref": None,
            },
        )
        assert stale_response.status_code == 409
        assert stale_response.json()["error"] == {
            "code": "revision_conflict",
            "message": stale_response.json()["error"]["message"],
            "request_id": "stale-thesis-transition",
            "issues": [],
        }

        unchanged = first_client.get(f"/api/v1/projects/{project_id}").json()
        assert unchanged["product_theses"][0]["status"] == "selected"
        assert unchanged["product_theses"][0]["meta"]["revision"] == 2

    with TestClient(create_app(database_path=database)) as restarted_client:
        response = restarted_client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        view = response.json()
        assert view["product_intent"]["status"] == "confirmed"
        assert view["problem_model"]["status"] == "confirmed"
        assert view["outcome_contract"]["status"] == "confirmed"
        assert view["product_theses"][0]["status"] == "selected"


def test_unconfirmed_upstream_returns_domain_gate_without_writing(tmp_path):
    with TestClient(
        create_app(database_path=tmp_path / "product-studio.sqlite3")
    ) as client:
        project_id = _create_project(client)
        intent_response = client.post(
            f"/api/v1/projects/{project_id}/product-intent/proposals",
            json={
                "proposal": intent_proposal(),
                "actor": "studio",
                "reason": "draft only",
            },
        )
        intent = intent_response.json()

        response = client.post(
            f"/api/v1/projects/{project_id}/problem-model/proposals",
            headers={"X-Request-ID": "unconfirmed-upstream"},
            json={
                "proposal": problem_proposal(intent["revision_id"]),
                "actor": "studio",
                "reason": "must be rejected",
            },
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "domain_gate"
        assert response.json()["error"]["request_id"] == "unconfirmed-upstream"
        view = client.get(f"/api/v1/projects/{project_id}").json()
        assert view["problem_model"] is None


def test_validation_error_does_not_echo_rejected_sensitive_input(tmp_path):
    sensitive_marker = "private-customer-secret-9f31"
    with TestClient(
        create_app(database_path=tmp_path / "product-studio.sqlite3")
    ) as client:
        project_id = _create_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/product-intent/proposals",
            headers={"X-Request-ID": "invalid-sensitive-input"},
            json={
                "proposal": {
                    "desired_change": sensitive_marker,
                    "affected_people": [],
                    "source_refs": [],
                },
                "actor": "studio",
                "reason": sensitive_marker,
            },
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["request_id"] == "invalid-sensitive-input"
    assert payload["error"]["issues"]
    assert sensitive_marker not in response.text


def test_openapi_exposes_every_product_command_schema():
    schema = create_app().openapi()
    components = schema["components"]["schemas"]
    required = {
        "CreateProjectRequest",
        "ChangeProjectStatusRequest",
        "SubmitProductIntentRequest",
        "SubmitProblemModelRequest",
        "SubmitOutcomeContractRequest",
        "SubmitProductThesisRequest",
        "ConfirmRevisionRequest",
        "TransitionProductThesisRequest",
        "ApiErrorResponse",
        "ProductProjectViewResponse",
        "CreateProposalJobRequest",
        "ProposalJobActionRequest",
        "ProductProposalJobResponse",
    }

    assert required <= set(components)
    assert schema["paths"]["/api/v1/projects/{project_id}"]["get"]["responses"]
    assert schema["paths"]["/api/v1/projects/{project_id}/proposal-jobs"]["post"][
        "responses"
    ]["202"]
