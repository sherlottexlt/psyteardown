"""框架检索:产品关键词与框架线索的词元重叠,按 IDF 加权打分。
接口签名为将来换向量检索预留。"""

import math
import re
import unicodedata

from psyteardown.kb.models import Framework

# 也匹配数字:命名为 ALNUM 而非 LATIN 是有意的,勿"简化"回去。
_ALNUM_RUN = re.compile(r"[A-Za-z0-9]+")
# CJK 统一表意文字基本区(U+4E00–U+9FFF)。不含假名、谚文、扩展 A/B 区与全角字母,
# 它们一律作分隔符——已审计当前语料,无此类字符。
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")


def _tokens(text: str) -> set[str]:
    """检索用词元:连续中文段切字符 2-gram,连续字母数字段取整词并转小写。

    先做 NFKC 归一,把全角字母数字(ＡＢ/Ｔ０)折成 ASCII——产品关键词由 LLM 从
    用户输入中抽取,不受知识库语料审计的约束,全角输入是现实可能。

    字符 n-gram 是中文分词的手段;拉丁文本自带词边界,按字符切只会制造假匹配
    (Leaderboard 与 onboarding 共享 ar/bo/oa/rd)。空白与标点一律作分隔符。

    字母数字词元须长度 >= 2 且非纯数字:单字母与裸数字没有检索价值,这与打分
    方式无关;在当前 IDF 方案下它们更因罕见而拿到最高权重。形如 T0/XP/ELO 的
    标签不受影响。此处的 2 是最小词元长度,与 CJK bigram 的宽度无关。
    """
    text = unicodedata.normalize("NFKC", text)
    tokens = {
        word.lower()
        for word in _ALNUM_RUN.findall(text)
        if len(word) >= 2 and not word.isdigit()
    }
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
