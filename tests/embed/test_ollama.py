"""OllamaEmbeddingProvider 单测:mock urllib,绝不触网。"""

import json

import pytest

from psyteardown.embed.ollama import OllamaEmbeddingProvider


class _FakeResp:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_embed_posts_batch_and_returns_vectors(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp({"embeddings": [[0.6, 0.8], [1.0, 0.0]]})

    import psyteardown.embed.ollama as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    p = OllamaEmbeddingProvider(model="bge-m3:567m", base_url="http://localhost:11434")
    vecs = p.embed(["文本甲", "文本乙"])

    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["body"] == {"model": "bge-m3:567m", "input": ["文本甲", "文本乙"]}
    assert vecs == [[0.6, 0.8], [1.0, 0.0]]
    assert p.dim == 2                      # dim 由首次结果缓存


def test_dim_before_embed_probes_once(monkeypatch):
    calls: list[dict] = []

    def fake_urlopen(req, timeout=None):
        calls.append(json.loads(req.data.decode("utf-8")))
        return _FakeResp({"embeddings": [[0.0] * 1024]})

    import psyteardown.embed.ollama as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    p = OllamaEmbeddingProvider()
    assert p.dim == 1024                   # 未 embed 先取 dim → 探测一次
    assert p.dim == 1024                   # 第二次走缓存
    assert len(calls) == 1


def test_base_url_env_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://10.0.0.5:11434/")
    p = OllamaEmbeddingProvider()
    assert p.base_url == "http://10.0.0.5:11434"   # 尾斜杠净化


def test_empty_input_no_request(monkeypatch):
    def boom(req, timeout=None):
        raise AssertionError("不应发请求")

    import psyteardown.embed.ollama as mod
    monkeypatch.setattr(mod, "urlopen", boom)
    assert OllamaEmbeddingProvider().embed([]) == []


def test_server_error_raises(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise OSError("connection refused")

    import psyteardown.embed.ollama as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    with pytest.raises(OSError):
        OllamaEmbeddingProvider().embed(["x"])


def test_missing_embeddings_key_raises(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResp({"error": "model not found"})

    import psyteardown.embed.ollama as mod
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="model not found"):
        OllamaEmbeddingProvider().embed(["x"])
