"""DeepSeekProvider 单测:mock urllib,绝不触网。"""

import json

import pytest
from pydantic import BaseModel

from psyteardown.llm.base import LLMError
from psyteardown.llm.deepseek import DeepSeekProvider


class _Out(BaseModel):
    name: str
    score: float


class _FakeResp:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _chat_payload(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LLMError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider()


def test_structured_complete_parses_and_sends_schema(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(_chat_payload('{"name": "demo", "score": 0.9}'))

    import psyteardown.llm.deepseek as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    p = DeepSeekProvider(api_key="sk-test", model="deepseek-chat")
    out = p.structured_complete("拆解这个产品", _Out, system="你是审阅者")

    assert out == _Out(name="demo", score=0.9)
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    body = captured["body"]
    assert body["model"] == "deepseek-chat"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][0]["role"] == "system"
    assert "你是审阅者" in body["messages"][0]["content"]
    assert "score" in body["messages"][0]["content"]      # schema 进 system 提示
    assert body["messages"][1] == {"role": "user", "content": "拆解这个产品"}


def test_structured_complete_strips_code_fence(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResp(_chat_payload('```json\n{"name": "x", "score": 0.1}\n```'))

    import psyteardown.llm.deepseek as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)
    out = DeepSeekProvider(api_key="k").structured_complete("p", _Out)
    assert out.name == "x"


def test_structured_complete_retries_then_fails(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        return _FakeResp(_chat_payload("这不是 JSON"))

    import psyteardown.llm.deepseek as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)
    p = DeepSeekProvider(api_key="k", max_retries=2)
    with pytest.raises(LLMError, match="重试后仍失败"):
        p.structured_complete("p", _Out)
    assert len(calls) == 3                    # 1 + 2 次重试


def test_complete_returns_text(monkeypatch):
    def fake_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        assert "response_format" not in body   # 纯文本不带 JSON mode
        return _FakeResp(_chat_payload("你好"))

    import psyteardown.llm.deepseek as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)
    assert DeepSeekProvider(api_key="k").complete("hi") == "你好"


def test_env_config(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://proxy.example.com/v1/")
    p = DeepSeekProvider()
    assert p.model == "deepseek-reasoner"
    assert p.base_url == "https://proxy.example.com/v1"   # 尾斜杠净化
