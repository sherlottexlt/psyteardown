"""用嵌入相似度 + id/name 过滤掉与现有框架重复的候选。"""

import numpy as np

from psyteardown.embed.base import EmbeddingProvider
from psyteardown.growth.models import FrameworkCandidate
from psyteardown.kb.models import Framework


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    return float(a @ b / (na * nb)) if na and nb else 0.0


def filter_duplicates(
    candidates: list[FrameworkCandidate],
    existing: list[Framework],
    embed: EmbeddingProvider | None = None,
    *,
    threshold: float = 0.85,
) -> list[FrameworkCandidate]:
    """丢弃 id/name 与现有冲突的候选;若给 embed,再丢弃 summary 余弦 ≥threshold 的。
    embed 为 None(如离线)时只做 id/name 去重。"""
    existing_ids = {f.id for f in existing}
    existing_names = {f.name for f in existing}

    ex_vecs: list[np.ndarray] | None = None
    if embed is not None and existing:
        ex_vecs = [np.asarray(v, dtype=np.float32)
                   for v in embed.embed([f.summary for f in existing])]

    kept: list[FrameworkCandidate] = []
    for cand in candidates:
        fw = cand.framework
        if fw.id in existing_ids or fw.name in existing_names:
            continue
        if ex_vecs is not None:
            cv = np.asarray(embed.embed([fw.summary])[0], dtype=np.float32)
            if any(_cos(cv, ev) >= threshold for ev in ex_vecs):
                continue
        kept.append(cand)
    return kept
