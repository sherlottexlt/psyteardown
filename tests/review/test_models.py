import pytest
from pydantic import ValidationError

from psyteardown.review.models import CaseReview


def test_defaults():
    r = CaseReview(score=0.7)
    assert r.strengths == []
    assert r.weaknesses == []
    assert r.suggestions == []
    assert r.reviewed_at == ""
    assert r.model == ""


def test_score_bounds_rejected():
    with pytest.raises(ValidationError):
        CaseReview(score=-0.1)
    with pytest.raises(ValidationError):
        CaseReview(score=1.1)


def test_json_roundtrip():
    r = CaseReview(score=0.6, strengths=["框架选得准"],
                   weaknesses=["社交证明置信虚高"],
                   suggestions=["先核对留存数据再定置信"],
                   reviewed_at="2026-07-16", model="fake")
    again = CaseReview.model_validate_json(r.model_dump_json())
    assert again.score == 0.6
    assert again.weaknesses == ["社交证明置信虚高"]
    assert again.reviewed_at == "2026-07-16"
