"""向量检索(暴力余弦)+ 案例摘要(供流水线参考注入)。"""

import numpy as np

from psyteardown.embed.base import EmbeddingProvider
from psyteardown.memory.models import Case
from psyteardown.memory.store import CaseStore, MemoryStoreError


def search_similar(
    store: CaseStore,
    provider: EmbeddingProvider,
    query_text: str,
    top_k: int = 3,
) -> list[tuple[Case, float]]:
    """query_text 向量化,与库中全部向量算余弦,返回 Top-K (Case, score)。
    空库 → [];维度不匹配 → MemoryStoreError。"""
    rows = store.all()
    if not rows:
        return []
    q = np.asarray(provider.embed([query_text])[0], dtype=np.float32)
    qn = float(np.linalg.norm(q))
    scored: list[tuple[Case, float]] = []
    for case, vec in rows:
        v = np.asarray(vec, dtype=np.float32)
        if v.shape != q.shape:
            raise MemoryStoreError(
                f"向量维度不匹配:库中 {v.shape[0]} vs 当前 provider {q.shape[0]}。"
                "换了嵌入模型须重建案例库。"
            )
        vn = float(np.linalg.norm(v))
        score = float(q @ v / (qn * vn)) if qn and vn else 0.0
        scored.append((case, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def summarize_cases(cases: list[Case]) -> str:
    """把相似案例压成精简参考摘要(产品名 + 一句话 + 用过的框架)。空 → ''。"""
    lines: list[str] = []
    for c in cases:
        fw = ", ".join(c.frameworks_used) or "—"
        lines.append(f"- {c.product_name}({c.one_liner}):用过框架 {fw}")
    return "\n".join(lines)
