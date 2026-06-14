import pytest
from pydantic import BaseModel

from psyteardown.llm.base import FakeProvider, LLMError


class Demo(BaseModel):
    value: str


def test_structured_complete_returns_queued_instance():
    provider = FakeProvider(structured_responses=[Demo(value="hi")])
    out = provider.structured_complete("prompt", Demo)
    assert isinstance(out, Demo)
    assert out.value == "hi"


def test_structured_complete_validates_dict_against_schema():
    provider = FakeProvider(structured_responses=[{"value": "ok"}])
    out = provider.structured_complete("prompt", Demo)
    assert out.value == "ok"


def test_complete_returns_queued_text():
    provider = FakeProvider(text_responses=["hello"])
    assert provider.complete("prompt") == "hello"


def test_exhausted_queue_raises():
    provider = FakeProvider(structured_responses=[])
    with pytest.raises(LLMError):
        provider.structured_complete("prompt", Demo)


def test_records_calls():
    provider = FakeProvider(text_responses=["a"])
    provider.complete("my-prompt", system="sys")
    assert provider.calls[0]["prompt"] == "my-prompt"
    assert provider.calls[0]["system"] == "sys"
