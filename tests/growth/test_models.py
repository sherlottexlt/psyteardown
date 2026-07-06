from psyteardown.growth.models import FrameworkCandidate, CandidateList
from psyteardown.kb.models import Framework, Principle


def _fw(id_="dark-urgency"):
    return Framework(
        id=id_, name="虚假紧迫", category="persuasion", summary="制造人为时间压力促成即时决策。",
        tags=["紧迫", "转化"],
        principles=[Principle(id="p", name="倒计时", description="d", look_for=["倒计时"])],
        references=["r"],
    )


def test_candidate_defaults():
    c = FrameworkCandidate(framework=_fw(), rationale="现有框架未覆盖")
    assert c.source_case_ids == []
    assert c.created_at == ""
    assert c.framework.id == "dark-urgency"


def test_candidate_json_roundtrip():
    c = FrameworkCandidate(framework=_fw(), rationale="r",
                           source_case_ids=["a", "b"], created_at="t")
    again = FrameworkCandidate.model_validate_json(c.model_dump_json())
    assert again.source_case_ids == ["a", "b"]
    assert again.framework.name == "虚假紧迫"


def test_candidate_list_wraps():
    cl = CandidateList(candidates=[])
    assert cl.candidates == []
