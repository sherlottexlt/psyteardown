"""grounding 纯函数:归一化 + 逐字子串判定。全部离线。

SOURCE 仿照 chaoxi.txt 的真实风格。关键背景(spec §5.1):step1 会把输入的半角
, ( ) 归一成全角 ，（ ）,不做归一化时真实引用的逐字命中率只有 1/9。
"""

from psyteardown.pipeline.grounding import MIN_QUOTE_CHARS, is_grounded, normalize

SOURCE = (
    "潮汐(Tide)是一款主打白噪音、专注计时与睡眠助眠的正念类App。"
    "白噪音音景库:雨声、海浪、森林、咖啡馆等自然与环境音,可单独播放或叠加混音,支持定时关闭;"
    "会员订阅:年费/月费解锁全部课程与高级音景,新用户有免费试用期,到期自动续费。"
)


def test_verbatim_quote_is_grounded():
    assert is_grounded("支持定时关闭", SOURCE)


def test_fullwidth_punctuation_difference_still_grounded():
    # 引用带全角逗号「，」,原文是半角「,」:归一化后仍应命中
    # (step1 实测就是这么改写标点的,spec §5.1:不归一化命中率只有 1/9)
    assert is_grounded("可单独播放或叠加混音，支持定时关闭", SOURCE)


def test_fullwidth_alnum_requires_nfkc():
    # isalnum() 过滤器自己就能吃掉全角标点(见上一条测试),不需要 NFKC 参与。
    # NFKC 唯一独有的作用是折叠全角字母/数字(０-９、Ａ-Ｚ→0-9、A-Z)。
    # 这条测试专门锁死这一点:去掉 normalize() 里的 NFKC 调用,本测试会失败
    # (已用变异测试验证,其余 9 条测试即使删掉 NFKC 也全绿)。
    source = "潮汐App限时优惠30分钟解锁全部音景。"
    assert is_grounded("限时优惠３０分钟解锁全部音景", source)


def test_quote_crossing_punctuation_is_grounded():
    # 引用跨越顿号:标点删除后是连续字符序列
    assert is_grounded("雨声、海浪、森林", SOURCE)


def test_cross_sentence_splice_is_known_false_positive():
    # 已知的、被接受的权衡(spec §9 第 3 条):normalize() 删除全部标点,包括句号「。」,
    # 所以两个语义无关、被句号分隔的独立句子,只要拼接处字符序列连续,就会被误判为
    # 「原文连续片段」。下面这句「续费潮汐App还支持每日」从未在原文里连续出现过——
    # 它是前一句的句尾接上后一句的句头拼出来的。
    #
    # 这条测试的目的不是背书这个行为,而是把它钉在回归套件里,不让它被意外发现。
    # 如果未来某次改动让这条测试变成 False,那是改进,应该更新/删掉这条测试,
    # 而不是去改回当前实现让它继续 True。
    source = "到期自动续费。潮汐App还支持每日提醒。"
    assert is_grounded("续费潮汐App还支持每日", source)


def test_prefix_rewording_not_grounded():
    # step1 实测改写模式:加「提供」前缀。归一化只救标点,不救真改写
    assert not is_grounded("提供雨声、海浪、森林", SOURCE)


def test_invented_detail_not_grounded():
    assert not is_grounded("连续打卡显示徽章", SOURCE)


def test_long_enough_quote_is_grounded():
    assert is_grounded("专注计时与睡眠助眠", SOURCE)


def test_quote_below_min_chars_not_grounded():
    # 「专注」是真原文子串,但两个字什么都证明不了(spec §5.2 长度门槛)
    assert not is_grounded("专注", SOURCE)


def test_empty_quote_not_grounded():
    assert not is_grounded("", SOURCE)


def test_casefold_folds_case():
    # casefold 折叠大小写:「APP」与原文里的「App」应视为同一序列
    assert is_grounded("正念类APP", SOURCE)


def test_normalize_strips_punctuation_whitespace_and_case():
    # 直接测 normalize:混合全角/半角标点、空白、大小写,归一化后只剩纯小写字母数字
    assert normalize("Hello, 世界! （测试） World.") == "hello世界测试world"


def test_min_quote_chars_locked():
    # 可调常量,但改动必须是显式决定,不能顺手
    assert MIN_QUOTE_CHARS == 6
