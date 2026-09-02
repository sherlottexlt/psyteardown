"""证据溯源:校验 evidence 是否为产品原文的逐字片段。

纯函数,不认识 LLM。归一化规则与实测依据见
docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md §5。
"""

import unicodedata

# 短于此的引用(归一化后计)判为未溯源:「专注」这类两字词天然是子串,
# 能通过校验却什么都证明不了。6 = 「支持定时关闭」这类最短有效引用的长度。
MIN_QUOTE_CHARS = 6


def normalize(text: str) -> str:
    """NFKC(全角→半角)→ casefold → 只留字母数字(一举去掉空白与全部标点,
    含 NFKC 不覆盖的 。、「」《》·—)。"""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in folded if ch.isalnum())


def is_grounded(quote: str, source: str) -> bool:
    """quote 归一化后长度达标、且是 source 归一化后的子串,才算可溯源。"""
    q = normalize(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in normalize(source)
