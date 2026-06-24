"""嵌入 provider 抽象。对称于 llm/:抽象 + Fake(测试)+ 真实默认实现。"""

import hashlib
from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量把文本转成等长向量。"""

    @property
    @abstractmethod
    def dim(self) -> int:
        """向量维度。"""


class FakeEmbeddingProvider(EmbeddingProvider):
    """测试用:确定性字符哈希 → 固定维向量,L2 归一化。绝不触网/不加载 torch。"""

    def __init__(self, dim: int = 64):
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            v = np.zeros(self._dim, dtype=np.float32)
            for ch in text:
                h = int(hashlib.sha256(ch.encode("utf-8")).hexdigest(), 16)
                v[h % self._dim] += 1.0
            norm = float(np.linalg.norm(v))
            if norm > 0:
                v = v / norm
            out.append(v.astype(float).tolist())
        return out
