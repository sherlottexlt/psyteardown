from psyteardown.kb.models import Framework, Principle


def test_framework_parses_from_dict():
    fw = Framework.model_validate(
        {
            "id": "fogg-behavior-model",
            "name": "Fogg 行为模型",
            "category": "motivation",
            "summary": "行为 = 动机 × 能力 × 提示。",
            "tags": ["行为触发", "习惯养成"],
            "principles": [
                {
                    "id": "trigger",
                    "name": "提示",
                    "description": "需要提示来触发行为。",
                    "look_for": ["推送", "红点"],
                }
            ],
            "references": ["Fogg, B.J. (2009)."],
            "ethics_notes": "可被用于暗黑模式。",
        }
    )
    assert fw.id == "fogg-behavior-model"
    assert fw.principles[0].look_for == ["推送", "红点"]
    assert fw.ethics_notes == "可被用于暗黑模式。"


def test_ethics_notes_optional():
    fw = Framework.model_validate(
        {
            "id": "x",
            "name": "X",
            "category": "cognition",
            "summary": "s",
            "tags": [],
            "principles": [],
            "references": [],
        }
    )
    assert fw.ethics_notes is None
