from psyteardown.kb.models import Framework, Principle
from psyteardown.kb.retriever import retrieve_frameworks


def _fw(id_, tags):
    return Framework(
        id=id_, name=id_, category="motivation", summary="s",
        tags=tags, principles=[Principle(id="p", name="p", description="d")],
        references=["r"],
    )


def test_keyword_match_ranks_higher():
    library = [
        _fw("habit", ["习惯养成", "留存"]),
        _fw("pricing", ["定价", "促销"]),
    ]
    result = retrieve_frameworks(library, keywords=["习惯养成"], top_n=2)
    assert result[0].id == "habit"


def test_no_match_falls_back_to_top_n():
    library = [_fw("a", ["x"]), _fw("b", ["y"]), _fw("c", ["z"])]
    result = retrieve_frameworks(library, keywords=["无关词"], top_n=2)
    assert len(result) == 2  # 无匹配也返回 top_n,保证流水线不空转


def test_respects_top_n_limit():
    library = [_fw(str(i), ["习惯养成"]) for i in range(10)]
    result = retrieve_frameworks(library, keywords=["习惯养成"], top_n=3)
    assert len(result) == 3


def test_partial_substring_match_counts():
    library = [_fw("a", ["习惯养成与留存"]), _fw("b", ["定价"])]
    result = retrieve_frameworks(library, keywords=["习惯"], top_n=1)
    assert result[0].id == "a"
