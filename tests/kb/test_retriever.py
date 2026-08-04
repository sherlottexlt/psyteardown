from psyteardown.kb.models import Framework, Principle
from psyteardown.kb.retriever import retrieve_frameworks, _tokens, _pool, _idf


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
    result = retrieve_frameworks(library, keywords=["习惯养成"], max_n=2)
    assert result[0].id == "habit"


def test_no_match_falls_back_to_floor():
    library = [_fw("a", ["x"]), _fw("b", ["y"]), _fw("c", ["z"])]
    result = retrieve_frameworks(library, keywords=["无关词"], max_n=2)
    assert len(result) == 2  # 无匹配也返回 floor 个,保证流水线不空转


def test_respects_max_n_limit():
    library = [_fw(str(i), ["习惯养成"]) for i in range(10)]
    result = retrieve_frameworks(library, keywords=["习惯养成"], max_n=3)
    assert len(result) == 3


def test_partial_bigram_match_counts():
    library = [_fw("a", ["习惯养成与留存"]), _fw("b", ["定价"])]
    result = retrieve_frameworks(library, keywords=["习惯"], max_n=1)
    assert result[0].id == "a"


def test_pads_to_min_n_when_few_nonzero():
    library = [_fw("hit", ["抽卡"])] + [_fw(f"z{i}", ["无关标签"]) for i in range(5)]
    result = retrieve_frameworks(library, keywords=["抽卡"], max_n=8, min_n=3)
    assert result[0].id == "hit"      # 命中的排第一
    assert len(result) == 3           # 其余按库序补齐到 min_n


def test_floor_never_exceeds_max_n():
    library = [_fw(str(i), ["无关"]) for i in range(6)]
    result = retrieve_frameworks(library, keywords=["查无此词"], max_n=2, min_n=5)
    assert len(result) == 2           # max_n 优先于 min_n


def test_floor_never_exceeds_library_size():
    library = [_fw("a", ["无关"]), _fw("b", ["无关"])]
    result = retrieve_frameworks(library, keywords=["查无此词"], max_n=8, min_n=5)
    assert len(result) == 2


def test_empty_library_returns_empty():
    assert retrieve_frameworks([], keywords=["任意"], max_n=5) == []


def test_non_positive_max_n_returns_empty():
    library = [_fw("a", ["抽卡"])]
    assert retrieve_frameworks(library, keywords=["抽卡"], max_n=0) == []


def test_blank_keywords_fall_back_to_floor():
    library = [_fw("a", ["抽卡"]), _fw("b", ["签到"]), _fw("c", ["排行"])]
    result = retrieve_frameworks(library, keywords=["", "  "], max_n=8, min_n=2)
    assert len(result) == 2  # 全零分 → 按库序补齐到 floor
    assert [fw.id for fw in result] == ["a", "b"]


def test_equal_scores_keep_library_order():
    library = [_fw("first", ["抽卡"]), _fw("second", ["抽卡"])]
    result = retrieve_frameworks(library, keywords=["抽卡"], max_n=2)
    assert [fw.id for fw in result] == ["first", "second"]


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
    assert _tokens("刷新 动画/特效") == {"刷新", "动画", "特效"}  # 空格与 / 均为分隔符


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
    # 隔离用例:字母被丢弃的同时,中文词元照常保留
    assert _tokens("X倍暴击") == {"倍暴", "暴击"}


def test_tokens_keeps_alnum_labels():
    assert _tokens("T0/T1 榜单") == {"t0", "t1", "榜单"}


def test_tokens_non_cjk_scripts_are_separators():
    # 仅覆盖 CJK 基本区;假名/谚文作分隔符(已审计当前语料无此类字符)
    assert _tokens("ガチャ") == set()
    assert _tokens("抽卡ガチャ保底") == {"抽卡", "保底"}


def test_tokens_normalizes_fullwidth_alnum():
    # 关键词由 LLM 从用户输入抽取,不受知识库审计约束,全角输入是现实可能
    assert _tokens("Ｔ０榜单") == {"t0", "榜单"}
    assert _tokens("ＡＢ测试") == {"ab", "测试"}


def _fw_with_clues(id_, tags, clues):
    return Framework(
        id=id_, name=id_, category="motivation", summary="s",
        tags=tags,
        principles=[Principle(id="p", name="p", description="d", look_for=clues)],
        references=["r"],
    )


def test_pool_includes_tags_and_look_for():
    fw = _fw_with_clues("a", ["抽卡"], ["重复点击"])
    pool = _pool(fw)
    assert "抽卡" in pool          # 来自 tags
    assert "重复" in pool          # 来自 look_for
    assert "点击" in pool


def test_pool_covers_every_principle():
    # 防回归:若实现只取 principles[0],本测试失败
    fw = Framework(
        id="a", name="a", category="motivation", summary="s",
        tags=["抽卡"],
        principles=[
            Principle(id="p1", name="p1", description="d", look_for=["重复点击"]),
            Principle(id="p2", name="p2", description="d", look_for=["限时倒计时"]),
        ],
        references=["r"],
    )
    pool = _pool(fw)
    assert "重复" in pool   # 第一条原则
    assert "倒计" in pool   # 第二条原则


def test_pool_empty_when_no_tags_no_clues():
    fw = _fw_with_clues("a", [], [])
    assert _pool(fw) == set()


def test_idf_common_bigram_weighs_zero():
    # "进度" 出现在全部 2 个池中 → log(2/2) = 0
    idf = _idf([{"进度", "抽卡"}, {"进度", "签到"}])
    assert idf["进度"] == 0.0


def test_idf_unique_bigram_weighs_most():
    idf = _idf([{"进度", "抽卡"}, {"进度", "签到"}])
    assert idf["抽卡"] > idf["进度"]
    assert idf["抽卡"] == idf["签到"]


def test_idf_ranks_by_document_frequency():
    # 三档 df:独有 > 部分共享 > 全库皆有;中间档才是真正决定排序的区间
    idf = _idf([{"抽卡", "进度", "通用"}, {"签到", "进度", "通用"}, {"排行", "通用"}])
    assert idf["通用"] == 0.0          # df=3/3
    assert idf["抽卡"] > idf["进度"]   # df=1 重于 df=2
    assert idf["进度"] > idf["通用"]


from psyteardown.kb.retriever import _score


def test_score_sums_idf_of_overlapping_bigrams():
    idf = {"抽卡": 2.0, "保底": 1.0}
    # 关键词 "抽卡保底" 的 bigram 为 {抽卡, 卡保, 保底};池中命中 抽卡 与 保底
    assert _score({"抽卡", "保底"}, ["抽卡保底"], idf) == 3.0


def test_score_zero_when_no_overlap():
    assert _score({"抽卡"}, ["每日签到"], {"抽卡": 2.0}) == 0.0


def test_score_ignores_bigram_missing_from_idf():
    assert _score({"抽卡"}, ["抽卡"], {}) == 0.0
