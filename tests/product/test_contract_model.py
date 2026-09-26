"""Unit tests for C0 real model provider (contract_model.py)."""

from __future__ import annotations

import json

from psyteardown.product.contract_model import (
    build_intent_prompt,
    parse_intent_reply,
)


def test_parse_intent_reply_valid_json():
    """parse_intent_reply returns ProductIntentProposal for valid JSON."""
    text = json.dumps({
        "desired_change": "Help knowledge workers maintain focus",
        "affected_people": ["remote workers", "freelancers"],
        "current_situation": "Frequent interruptions break concentration",
        "explicit_non_goals": ["employee monitoring"],
        "known_constraints": ["must work offline"],
        "resource_preferences": ["low maintenance"],
    })
    result = parse_intent_reply(text, job_id="test-job")
    # Check it's not a list of errors
    assert not isinstance(result, list)
    assert result.desired_change == "Help knowledge workers maintain focus"
    assert result.affected_people == ["remote workers", "freelancers"]


def test_parse_intent_reply_missing_desired_change():
    """parse_intent_reply rejects JSON without desired_change."""
    text = json.dumps({"affected_people": []})
    result = parse_intent_reply(text, job_id="test-job")
    assert isinstance(result, list)
    assert "desired_change" in result[0]


def test_parse_intent_reply_invalid_json():
    """parse_intent_reply rejects invalid JSON."""
    result = parse_intent_reply("not json", job_id="test-job")
    assert isinstance(result, list)
    assert "not valid JSON" in result[0]


def test_build_intent_prompt():
    """build_intent_prompt includes user input."""
    prompt = build_intent_prompt("Help me focus better")
    assert "Help me focus better" in prompt


def test_thesis_prompt_freezes_realization_mode_allowlist():
    from psyteardown.product.contract_model import THESIS_SYSTEM

    assert '"software", "hardware", "service", "content", "process", "hybrid"' in THESIS_SYSTEM
    assert 'Do not invent values' in THESIS_SYSTEM
