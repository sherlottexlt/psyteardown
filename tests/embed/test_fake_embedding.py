import math

from psyteardown.embed.base import EmbeddingProvider, FakeEmbeddingProvider


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def test_is_embedding_provider():
    assert isinstance(FakeEmbeddingProvider(), EmbeddingProvider)


def test_dim_matches_vector_length():
    p = FakeEmbeddingProvider(dim=32)
    assert p.dim == 32
    [vec] = p.embed(["你好"])
    assert len(vec) == 32


def test_same_text_same_vector():
    p = FakeEmbeddingProvider()
    [a] = p.embed(["每日签到App"])
    [b] = p.embed(["每日签到App"])
    assert a == b


def test_identical_text_cosine_is_one():
    p = FakeEmbeddingProvider()
    [a] = p.embed(["每日签到App"])
    assert _cos(a, a) == 1.0 or abs(_cos(a, a) - 1.0) < 1e-6


def test_batch_returns_one_vector_per_text():
    p = FakeEmbeddingProvider()
    vecs = p.embed(["a", "bb", "ccc"])
    assert len(vecs) == 3
    assert all(len(v) == p.dim for v in vecs)


def test_overlapping_text_more_similar_than_disjoint():
    p = FakeEmbeddingProvider()
    [base] = p.embed(["签到打卡习惯养成推送"])
    [near] = p.embed(["签到打卡习惯养成"])
    [far] = p.embed(["金融理财股票基金"])
    assert _cos(base, near) > _cos(base, far)
