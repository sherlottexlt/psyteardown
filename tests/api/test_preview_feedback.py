from fastapi.testclient import TestClient

from psyteardown.api.app import create_app
from .test_delivery_bundles import _verified_execution


def _bundle(client: TestClient) -> tuple[str, dict, dict]:
    project_id, executed = _verified_execution(client)
    bundle = client.post(
        f"/api/v1/projects/{project_id}/delivery-bundles",
        json={"execution_job_id": executed["job_id"], "actor": "user-li", "reason": "deliver"},
    ).json()
    contract = client.get(f"/api/v1/projects/{project_id}").json()["web_generation_contract"]
    return project_id, bundle, contract


def _feedback_body(contract: dict, **overrides) -> dict:
    screen = contract["screens"][0]
    body = {
        "screen_id": screen["screen_id"],
        "task_id": screen["task_ids"][0],
        "category": "bug",
        "text": "Stop does not explain what happens to the session.",
        "actor": "local-user",
        "consent_version": "b7-explicit-v1",
        "consent_granted": True,
    }
    body.update(overrides)
    return body


def test_preview_is_sandboxed_and_serves_only_delivered_build(tmp_path):
    with TestClient(create_app(database_path=tmp_path / "product.sqlite3")) as client:
        project_id, bundle, _ = _bundle(client)
        base = f"/api/v1/projects/{project_id}/delivery-bundles/{bundle['bundle_id']}/preview/"

        index = client.get(base)
        assert index.status_code == 200
        assert index.headers["content-type"].startswith("text/html")
        csp = index.headers["content-security-policy"]
        assert "sandbox allow-scripts" in csp and "connect-src 'none'" in csp
        assert "allow-same-origin" not in csp
        assert index.headers["x-content-type-options"] == "nosniff"
        assert index.headers["access-control-allow-origin"] == "*"

        asset = client.get(base + "assets/index.js")
        assert asset.status_code == 200
        assert asset.headers["content-type"].startswith("text/javascript")

        assert client.get(base + "DELIVERY.md").status_code == 404
        assert client.get(base + "missing.css").status_code == 404
        assert client.get(f"/api/v1/projects/{project_id}/delivery-bundles/delivery-bundle-x/preview/").status_code == 404


def test_feedback_api_requires_consent_and_supports_withdrawal_after_restart(tmp_path):
    database = tmp_path / "product.sqlite3"
    with TestClient(create_app(database_path=database)) as client:
        policy = client.get("/api/v1/preview-feedback-policy").json()
        assert policy["consent_version"] == "b7-explicit-v1"
        assert "clicks" in policy["not_captured"]

        project_id, bundle, contract = _bundle(client)
        url = f"/api/v1/projects/{project_id}/delivery-bundles/{bundle['bundle_id']}/feedback"

        no_consent = client.post(url, json=_feedback_body(contract, consent_granted=False))
        assert no_consent.status_code == 409
        assert no_consent.json()["error"]["code"] == "domain_gate"
        stale_policy = client.post(url, json=_feedback_body(contract, consent_version="b7-explicit-v0"))
        assert stale_policy.status_code == 409
        wrong_anchor = client.post(url, json=_feedback_body(contract, screen_id="screen-unknown"))
        assert wrong_anchor.status_code == 409
        too_long = client.post(url, json=_feedback_body(contract, text="x" * 2001))
        assert too_long.status_code == 422
        assert client.get(f"/api/v1/projects/{project_id}/preview-feedback").json() == []

        created = client.post(url, json=_feedback_body(contract))
        assert created.status_code == 201
        feedback = created.json()
        assert feedback["delivery_bundle_revision_id"] == bundle["revision_id"]
        assert feedback["evidence_level"] == "user_report"
        assert feedback["automatic_capture"] == "none"

    with TestClient(create_app(database_path=database)) as restarted:
        listed = restarted.get(
            f"/api/v1/projects/{project_id}/preview-feedback", params={"bundle_id": bundle["bundle_id"]}
        ).json()
        assert [item["feedback_id"] for item in listed] == [feedback["feedback_id"]]
        withdrawal = f"/api/v1/projects/{project_id}/preview-feedback/{feedback['feedback_id']}/withdrawal"
        other = restarted.post(withdrawal, json={"actor": "someone-else", "expected_revision": 1})
        assert other.status_code == 409
        withdrawn = restarted.post(withdrawal, json={"actor": "local-user", "expected_revision": 1})
        assert withdrawn.status_code == 200
        assert withdrawn.json()["status"] == "withdrawn"
        assert withdrawn.json()["text"] is None
        conflict = restarted.post(withdrawal, json={"actor": "local-user", "expected_revision": 1})
        assert conflict.status_code == 409
        missing = restarted.post(
            f"/api/v1/projects/{project_id}/preview-feedback/preview-feedback-x/withdrawal",
            json={"actor": "local-user", "expected_revision": 1},
        )
        assert missing.status_code == 404
