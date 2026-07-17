"""Ollama 嵌入实现:走本地 Ollama /api/embed,纯标准库,零新依赖。"""

import json
import os
from urllib.request import Request, urlopen

from psyteardown.embed.base import EmbeddingProvider

DEFAULT_MODEL = "bge-m3:567m"
DEFAULT_BASE_URL = "http://localhost:11434"
_TIMEOUT_SECONDS = 120


class OllamaEmbeddingProvider(EmbeddingProvider):
    """构造廉价;每次 embed() 批量 POST。base_url 可被 OLLAMA_HOST 环境变量覆盖。"""

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str | None = None):
        self.model = model
        raw = base_url or os.environ.get("OLLAMA_HOST") or DEFAULT_BASE_URL
        self.base_url = raw.rstrip("/")
        self._dim: int | None = None

    @property
    def dim(self) -> int:
        if self._dim is None:
            self.embed(["dim 探测"])
        assert self._dim is not None
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        req = Request(
            f"{self.base_url}/api/embed",
            data=json.dumps({"model": self.model, "input": texts}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if "embeddings" not in payload:
            raise RuntimeError(f"Ollama 嵌入失败:{payload.get('error', payload)}")
        vecs = [[float(x) for x in v] for v in payload["embeddings"]]
        if vecs:
            self._dim = len(vecs[0])
        return vecs
