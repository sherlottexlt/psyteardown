from psyteardown.embed.base import FakeEmbeddingProvider
from psyteardown.growth.dedup import filter_duplicates
from psyteardown.growth.models import FrameworkCandidate
from psyteardown.kb.models import Framework, Principle


def _fw(id_, name, summary):
    return Framework(id=id_, name=name, category="x", summary=summary, tags=["t"],
                     principles=[Principle(id="p", name="p", description="d")],
                     references=["r"])


def _cand(id_, name, summary):
    return FrameworkCandidate(framework=_fw(id_, name, summary), rationale="r")


def test_id_clash_dropped():
    existing = [_fw("dup", "已有", "已有摘要")]
    cands = [_cand("dup", "新名", "完全不同的摘要内容")]
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider())
    assert out == []


def test_name_clash_dropped():
    existing = [_fw("a", "同名框架", "摘要甲")]
    cands = [_cand("b", "同名框架", "摘要乙")]
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider())
    assert out == []


def test_semantically_similar_dropped():
    existing = [_fw("a", "框架甲", "签到打卡习惯养成推送提醒")]
    cands = [_cand("b", "框架乙", "签到打卡习惯养成推送")]     # 高度相似
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider(), threshold=0.9)
    assert out == []


def test_distinct_kept():
    existing = [_fw("a", "框架甲", "金融理财股票基金")]
    cands = [_cand("b", "框架乙", "签到打卡习惯养成推送")]
    out = filter_duplicates(cands, existing, embed=FakeEmbeddingProvider(), threshold=0.9)
    assert [c.framework.id for c in out] == ["b"]


def test_no_embed_falls_back_to_id_name_only():
    existing = [_fw("a", "框架甲", "签到打卡习惯养成推送提醒")]
    cands = [_cand("b", "框架乙", "签到打卡习惯养成推送")]     # 语义相似但 id/name 不同
    out = filter_duplicates(cands, existing, embed=None)      # 无嵌入 → 只按 id/name
    assert [c.framework.id for c in out] == ["b"]             # 相似但仍保留
