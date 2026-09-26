from __future__ import annotations

from psyteardown.product.stability import aggregate_c3_runs, sanitize_c3_run


def _run(*, success: bool = True, calls: int = 2, failures: list[dict] | None = None) -> dict:
    return {
        "total_time_seconds": 12.5,
        "project_id": "secret-project-id-must-not-leak",
        "steps": [
            {
                "step": "generate_source",
                "time": 2.5,
                "success": success,
                "provider": "deepseek",
                "model_calls": [
                    {
                        "provider": "deepseek",
                        "model": "deepseek-chat",
                        "outcome": "accepted",
                        "input_tokens": 10,
                        "output_tokens": 20,
                        "duration_seconds": 1.5,
                        "prompt": "secret prompt",
                    }
                    for _ in range(calls)
                ],
            },
            {"step": "export_b6", "time": 1.0, "success": success, "archive_bytes": 123},
        ],
        "model_usage": {
            "contract_provider": [
                {"provider": "deepseek", "model": "deepseek-chat", "outcome": "accepted", "input_tokens": 30, "output_tokens": 40}
            ],
        },
        "failures": failures or ([] if success else [{"step": "generate_source", "error_code": "model_output_rejected", "error_summary": "secret raw error"}]),
        "recovered_failures": [] if success else [{"step": "generate_source", "error_code": "command_failed"}],
    }


def test_sanitize_c3_run_only_emits_allowlisted_operational_fields():
    result = sanitize_c3_run(1, _run())
    text = str(result)
    assert "secret-project-id" not in text
    assert "secret prompt" not in text
    assert "secret raw error" not in text
    assert result["complete_success"] is True
    assert result["model_usage"] == {"total_calls": 3, "input_tokens": 50, "output_tokens": 80}
    assert result["recovered_failure_codes"] == []


def test_sanitize_handles_partial_failure_and_missing_usage():
    result = sanitize_c3_run(2, {"steps": [{"step": "generate_intent", "success": False}], "failures": [{"step": "generate_intent"}]})
    assert result["status"] == "failed"
    assert result["failure_codes"] == ["generate_intent_failed"]
    assert result["model_usage"] == {"total_calls": 0, "input_tokens": 0, "output_tokens": 0}


def test_aggregate_reports_failure_modes_tokens_and_success_rate():
    report = aggregate_c3_runs([sanitize_c3_run(1, _run()), sanitize_c3_run(2, _run(success=False))])
    assert report["runs_attempted"] == 2
    assert report["runs_succeeded"] == 1
    assert report["success_rate"] == 0.5
    assert report["failure_modes"] == {"model_output_rejected": 1}
    assert report["recovered_failure_modes"] == {"command_failed": 1}
    assert report["token_totals"] == {"input_tokens": 100, "output_tokens": 160}
    assert report["budget"]["monetary_cost"] == "unavailable_not_inferred"
    assert report["complete"] is False


def test_aggregate_stops_at_model_call_budget_boundary():
    runs = [sanitize_c3_run(index, _run(calls=2)) for index in range(1, 4)]
    report = aggregate_c3_runs(runs, required_runs=3, max_model_calls=5)
    assert report["budget"]["model_calls"] == 9
    assert report["stop_reason"] == "model_call_budget_exceeded"
    assert report["complete"] is False


def test_aggregate_can_report_reserved_budget_stop_without_exceeding_cap():
    runs = [sanitize_c3_run(index, _run(calls=2)) for index in range(1, 3)]
    report = aggregate_c3_runs(
        runs, required_runs=3, max_model_calls=10, stop_reason="insufficient_reserved_call_budget_for_next_run"
    )
    assert report["budget"]["model_calls"] == 6
    assert report["stop_reason"] == "insufficient_reserved_call_budget_for_next_run"
    assert report["complete"] is False


def test_outer_c3_run_timeout_remains_distinct_from_b4_browser_timeout():
    run = sanitize_c3_run(1, {
        "steps": [],
        "failures": [{"step": "run", "error_code": "run_timeout"}],
    })
    assert run["failure_codes"] == ["run_timeout"]
    assert run["complete_success"] is False

    browser_run = sanitize_c3_run(2, {
        "steps": [{"step": "execute_b4", "success": False}],
        "failures": [{"step": "execute_b4", "error_code": "browser_timeout"}],
    })
    assert browser_run["failure_codes"] == ["browser_timeout"]
    assert browser_run["failure_codes"] != run["failure_codes"]
