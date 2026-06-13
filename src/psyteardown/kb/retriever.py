"""框架检索:v1 用标签/关键词子串匹配打分。接口签名为将来换向量检索预留。"""

from psyteardown.kb.models import Framework


def _score(framework: Framework, keywords: list[str]) -> int:
    """每个关键词若是某 tag 的子串(或反之)记 1 分。"""
    score = 0
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        for tag in framework.tags:
            if kw in tag or tag in kw:
                score += 1
                break
    return score


def retrieve_frameworks(
    library: list[Framework],
    keywords: list[str],
    top_n: int = 5,
) -> list[Framework]:
    """按关键词与 tags 的匹配度返回 Top-N 框架;无匹配则返回前 top_n(稳定不空转)。"""
    ranked = sorted(
        library,
        key=lambda f: (_score(f, keywords), -ord(f.id[0]) if f.id else 0),
        reverse=True,
    )
    return ranked[:top_n]
