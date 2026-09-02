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


def test_quote_crossing_punctuation_is_grounded():
    # 引用跨越顿号:标点删除后是连续字符序列
    assert is_grounded("雨声、海浪、森林", SOURCE)


def test_prefix_rewording_not_grounded():
    # step1 实测改写模式:加「提供」前缀。归一化只救标点,不救真改写
    assert not is_grounded("提供雨声、海浪、森林", SOURCE)


def test_invented_detail_not_grounded():
    assert not is_grounded("连续打卡显示徽章", SOURCE)


def test_short_quote_not_grounded():
    # 「专注」是真原文子串,但两个字什么都证明不了(spec §5.2 长度门槛)
    assert is_grounded("专注计时与睡眠助眠", SOURCE)
    assert not is_grounded("专注", SOURCE)


def test_empty_quote_not_grounded():
    assert not is_grounded("", SOURCE)


def test_casefold_and_fullwidth_alnum():
    # casefold 折叠大小写;NFKC 折叠全角字母数字
    assert is_grounded("正念类APP", SOURCE)


def test_min_quote_chars_locked():
    # 可调常量,但改动必须是显式决定,不能顺手
    assert MIN_QUOTE_CHARS == 6
