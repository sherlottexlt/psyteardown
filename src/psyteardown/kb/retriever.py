"""框架检索:产品关键词与框架线索的字符 bigram 重叠,按 IDF 加权打分。
接口签名为将来换向量检索预留。"""

import math
import re

from psyteardown.kb.models import Framework

_LATIN_RUN = re.compile(r"[A-Za-z0-9]+")
_CJK_RUN = re.compile(r"[一-鿿]+")


def _tokens(text: str) -> set[str]:
    """检索用词元:连续中文段切字符 2-gram,连续拉丁/数字段取整词并转小写。

    字符 n-gram 是中文分词的手段;拉丁文本自带词边界,按字符切只会制造假匹配
    (Leaderboard 与 onboarding 共享 ar/bo/oa/rd)。空白与标点一律作分隔符。
    """
    tokens = {word.lower() for word in _LATIN_RUN.findall(text)}
    for run in _CJK_RUN.findall(text):
        tokens |= {run[i:i + 2] for i in range(len(run) - 1)}
    return tokens


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
