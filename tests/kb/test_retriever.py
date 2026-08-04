from psyteardown.kb.models import Framework, Principle
from psyteardown.kb.retriever import retrieve_frameworks, _tokens


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


def test_tokens_splits_chinese_into_bigrams():
    assert _tokens("抽卡保底") == {"抽卡", "卡保", "保底"}


def test_tokens_keeps_latin_as_whole_lowercase_word():
    assert _tokens("Leaderboard") == {"leaderboard"}


def test_tokens_latin_does_not_collide_by_characters():
    # 回归:曾按字符切分,Leaderboard 与 onboarding 共享 ar/bo/oa/rd 造成假阳性
    assert _tokens("Leaderboard") & _tokens("onboarding") == set()


def test_tokens_mixed_script():
    assert _tokens("自走棋/Auto Battler手游") == {
        "自走", "走棋", "auto", "battler", "手游",
    }


def test_tokens_punctuation_and_space_separate():
    assert _tokens("刷新 动画/特效") == {"刷新", "动画", "特效"}  # 不再跨隙产生「新动」


def test_tokens_two_chars_is_boundary():
    assert _tokens("卡片") == {"卡片"}


def test_tokens_dedups_repeats():
    assert _tokens("卡卡卡") == {"卡卡"}


def test_tokens_too_short_returns_empty():
    assert _tokens("卡") == set()
    assert _tokens("") == set()
    assert _tokens("、,。") == set()


def test_tokens_drops_bare_digits_and_single_letters():
    # 语义为空却因罕见拿到最高 IDF,属与拉丁字符切分同类的假阳性
    assert _tokens("第0天") == set()
    assert _tokens("99") == set()
    assert _tokens("X倍") == set()


def test_tokens_keeps_alnum_labels():
    assert _tokens("T0/T1 榜单") == {"t0", "t1", "榜单"}


def test_tokens_non_cjk_scripts_are_separators():
    # 仅覆盖 CJK 基本区;假名/谚文作分隔符(已审计当前语料无此类字符)
    assert _tokens("ガチャ") == set()
    assert _tokens("抽卡ガチャ保底") == {"抽卡", "保底"}
