"""Pure aggregation and redaction helpers for the C3 real-provider stability run.

The runner deliberately keeps raw C0 artifacts out of the aggregate report.  This
module accepts the existing C0 diagnostic shape, but emits only a small,
allow-listed operational summary suitable for committing or sharing.
"""

from __future__ import annotations

from collections import Counter
from numbers import Real
from typing import Any, Iterable

C3_REQUIRED_RUNS = 10
C3_MAX_MODEL_CALLS = 100
C3_MAX_MODEL_CALLS_PER_RUN = 10

_ALLOWED_STAGE_KEYS = {
    "step",
    "time",
    "success",
    "provider",
    "model",
    "execution_steps",
    "model_calls",
    "archive_sha256",
    "archive_bytes",
}
_ALLOWED_MODEL_CALL_KEYS = {
    "provider",
    "model",
    "outcome",
    "input_tokens",
    "output_tokens",
    "duration_seconds",
}


def _number(value: Any, *, integer: bool = False) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    if integer:
        return int(value)
    return float(value)


def _safe_error_code(failure: Any) -> str:
    if not isinstance(failure, dict):
        return "unknown_failure"
    value = failure.get("error_code")
    if isinstance(value, str) and value and len(value) <= 80:
        return value
    step = failure.get("step")
    if isinstance(step, str) and step and len(step) <= 80:
        return f"{step}_failed"
    return "unknown_failure"


def _sanitize_model_call(call: Any) -> dict[str, Any]:
    if not isinstance(call, dict):
        return {"outcome": "unknown"}
    result: dict[str, Any] = {}
    for key in _ALLOWED_MODEL_CALL_KEYS:
        value = call.get(key)
        if key in {"input_tokens", "output_tokens"}:
            result[key] = _number(value, integer=True)
        elif key == "duration_seconds":
            result[key] = _number(value)
        elif isinstance(value, str) and len(value) <= 80:
            result[key] = value
    return result


def _stage_status(stage: dict[str, Any]) -> str:
    return "succeeded" if stage.get("success") is True else "failed"


def sanitize_c3_run(run_number: int, metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Return an allow-listed summary of one C0-shaped run.

    This function never copies project IDs, prompts, responses, transcript paths,
    full errors, or arbitrary input fields.
    """

    if not isinstance(run_number, int) or run_number < 1:
        raise ValueError("run_number must be a positive integer")
    source = metrics if isinstance(metrics, dict) else {}
    stages: list[dict[str, Any]] = []
    total_calls = 0
    input_tokens = 0
    output_tokens = 0
    for raw_stage in source.get("steps", ()):
        if not isinstance(raw_stage, dict):
            continue
        stage: dict[str, Any] = {
            "name": raw_stage.get("step") if isinstance(raw_stage.get("step"), str) else "unknown_stage",
            "status": _stage_status(raw_stage),
        }
        elapsed = _number(raw_stage.get("time"))
        if elapsed is not None:
            stage["time_seconds"] = elapsed
        for source_key, target_key in (("provider", "provider"), ("archive_sha256", "archive_sha256")):
            value = raw_stage.get(source_key)
            if isinstance(value, str) and len(value) <= 128:
                stage[target_key] = value
        archive_bytes = _number(raw_stage.get("archive_bytes"), integer=True)
        if archive_bytes is not None:
            stage["archive_bytes"] = archive_bytes
        execution_steps = raw_stage.get("execution_steps")
        if isinstance(execution_steps, list) and all(isinstance(item, str) and len(item) <= 40 for item in execution_steps):
            stage["execution_steps"] = list(execution_steps)

        calls = raw_stage.get("model_calls")
        if isinstance(calls, list):
            safe_calls = [_sanitize_model_call(call) for call in calls]
            stage["model_calls"] = safe_calls
            stage["call_count"] = len(safe_calls)
            total_calls += len(safe_calls)
            input_tokens += sum(item.get("input_tokens") or 0 for item in safe_calls)
            output_tokens += sum(item.get("output_tokens") or 0 for item in safe_calls)
        stages.append(stage)

    usage = source.get("model_usage")
    if isinstance(usage, dict):
        contract_calls = usage.get("contract_provider")
        if isinstance(contract_calls, list):
            safe_contract = [_sanitize_model_call(call) for call in contract_calls]
            stage = {
                "name": "product_contract_provider",
                "status": "succeeded" if all(call.get("outcome") != "failed" for call in safe_contract) else "failed",
                "model_calls": safe_contract,
                "call_count": len(safe_contract),
            }
            stages.insert(0, stage)
            total_calls += len(safe_contract)
            input_tokens += sum(item.get("input_tokens") or 0 for item in safe_contract)
            output_tokens += sum(item.get("output_tokens") or 0 for item in safe_contract)
        source_calls = usage.get("source_provider")
        if isinstance(source_calls, list) and not any("model_calls" in item for item in stages):
            safe_source = [_sanitize_model_call(call) for call in source_calls]
            stages.append({
                "name": "source_model_provider",
                "status": "succeeded" if all(call.get("outcome") != "failed" for call in safe_source) else "failed",
                "model_calls": safe_source,
                "call_count": len(safe_source),
            })
            total_calls += len(safe_source)
            input_tokens += sum(item.get("input_tokens") or 0 for item in safe_source)
            output_tokens += sum(item.get("output_tokens") or 0 for item in safe_source)

    failures = source.get("failures")
    failure_codes = [_safe_error_code(item) for item in failures] if isinstance(failures, list) else []
    recovered = source.get("recovered_failures")
    recovered_failure_codes = [_safe_error_code(item) for item in recovered] if isinstance(recovered, list) else []
    complete_success = not failure_codes and any(item["name"] == "export_b6" and item["status"] == "succeeded" for item in stages)
    total_time = _number(source.get("total_time_seconds"))
    if total_time is None:
        total_time = _number(source.get("total_time"))

    return {
        "run_number": run_number,
        "status": "succeeded" if complete_success else "failed",
        "complete_success": complete_success,
        "total_time_seconds": total_time,
        "stages": stages,
        "failure_codes": failure_codes,
        "recovered_failure_codes": recovered_failure_codes,
        "model_usage": {
            "total_calls": total_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


def aggregate_c3_runs(
    runs: Iterable[dict[str, Any]],
    *,
    required_runs: int = C3_REQUIRED_RUNS,
    max_model_calls: int = C3_MAX_MODEL_CALLS,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    """Aggregate sanitized runs and expose a deterministic completion verdict."""

    if required_runs < 1 or max_model_calls < 1:
        raise ValueError("C3 limits must be positive")
    sanitized = [item for item in runs if isinstance(item, dict)]
    total_calls = sum(int((item.get("model_usage") or {}).get("total_calls") or 0) for item in sanitized)
    if total_calls > max_model_calls:
        stop_reason = "model_call_budget_exceeded"
    failure_counts = Counter(
        code
        for item in sanitized
        for code in item.get("failure_codes", ())
        if isinstance(code, str)
    )
    recovered_failure_counts = Counter(
        code
        for item in sanitized
        for code in item.get("recovered_failure_codes", ())
        if isinstance(code, str)
    )
    successful = sum(1 for item in sanitized if item.get("complete_success") is True)
    token_pairs = [
        {
            "run_number": item.get("run_number"),
            "input_tokens": int((item.get("model_usage") or {}).get("input_tokens") or 0),
            "output_tokens": int((item.get("model_usage") or {}).get("output_tokens") or 0),
        }
        for item in sanitized
    ]
    return {
        "schema_version": "c3-v1",
        "required_runs": required_runs,
        "runs_attempted": len(sanitized),
        "runs_succeeded": successful,
        "success_rate": (successful / len(sanitized)) if sanitized else 0.0,
        "complete": len(sanitized) == required_runs and stop_reason is None,
        "stop_reason": stop_reason,
        "budget": {
            "max_model_calls": max_model_calls,
            "model_calls": total_calls,
            "monetary_cost": "unavailable_not_inferred",
        },
        "failure_modes": dict(sorted(failure_counts.items())),
        "recovered_failure_modes": dict(sorted(recovered_failure_counts.items())),
        "token_totals": {
            "input_tokens": sum(item["input_tokens"] for item in token_pairs),
            "output_tokens": sum(item["output_tokens"] for item in token_pairs),
        },
        "per_run_tokens": token_pairs,
        "runs": sanitized,
    }
