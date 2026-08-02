"""框架检索:产品关键词与框架线索的字符 bigram 重叠,按 IDF 加权打分。
接口签名为将来换向量检索预留。"""

import math

from psyteardown.kb.models import Framework


def _bigrams(text: str) -> set[str]:
    """取字符 2-gram;先去掉所有空白。长度 < 2 → 空集。"""
    s = "".join(text.split())
    return {s[i:i + 2] for i in range(len(s) - 1)}


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
    # 仅按匹配分降序;Python 的 sort 稳定,同分时保持原库顺序。
    ranked = sorted(library, key=lambda f: _score(f, keywords), reverse=True)
    return ranked[:top_n]
