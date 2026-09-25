from fastapi.testclient import TestClient

from psyteardown.api.app import create_app
from tests.product.source_model_fixtures import ScriptedSourceModel, reply_for
from .test_generation_jobs import _confirmed_web_contract


def test_model_generation_is_unavailable_without_a_configured_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("PSYTEARDOWN_PRODUCT_SOURCE_MODEL", raising=False)
    monkeypatch.delenv("PSYTEARDOWN_LLM", raising=False)
    monkeypatch.setenv("PSYTEARDOWN_ENV_FILE", str(tmp_path / "missing.env"))
    with TestClient(create_app(database_path=tmp_path / "product.sqlite3")) as client:
        policy = client.get("/api/v1/source-model-policy").json()
        assert policy["available"] is False
        assert "original user input" in policy["not_sent"]
        assert policy["model_writes"] == ["src/App.tsx", "src/styles.css"]
        assert policy["repair_uses_model"] is False
        project_id, _ = _confirmed_web_contract(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs",
            json={"actor": "user-li", "reason": "model draft", "source": "model"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "domain_gate"


def test_model_job_records_calls_and_serves_the_local_transcript(tmp_path):
    model = ScriptedSourceModel(reply_for("export default function App() { return null; }\n"))
    database = tmp_path / "product.sqlite3"
    with TestClient(create_app(database_path=database, source_model=model)) as client:
        policy = client.get("/api/v1/source-model-policy").json()
        assert policy["available"] is True and policy["provider"] == "scripted"
        project_id, _ = _confirmed_web_contract(client)
        job = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs",
            json={"actor": "user-li", "reason": "model draft", "source": "model"},
        ).json()
        assert job["provider"] == "model_source" and job["budget"]["max_cost_units"] == 2
        run = client.post(
            f"/api/v1/projects/{project_id}/generation-jobs/{job['job_id']}/runs", json={"actor": "local-worker"}
        ).json()
        assert run["status"] == "failed" and run["error_code"] == "model_output_rejected"
        assert run["model_calls"][0]["outcome"] == "rejected"

    with TestClient(create_app(database_path=database, source_model=model)) as restarted:
        base = f"/api/v1/projects/{project_id}/generation-jobs/{job['job_id']}/model-calls"
        transcript = restarted.get(f"{base}/1").json()
        assert transcript["response"].startswith("```tsx")
        assert transcript["gate"]["accepted"] is False
        assert "Confirmed Web generation contract" in transcript["prompt"]
        assert restarted.get(f"{base}/2").status_code == 404
