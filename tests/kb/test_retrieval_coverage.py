"""非游戏品类的检索覆盖:三个验证画像的头名框架必须语义正确。

设计要点(改动前请先读):
- 画像各 12 个关键词,匹配 step1 真实产出的丰度(实测既有 6 案例为 12~19 词)。
  用 3 个关键词的稀疏画像测出的"零覆盖"是假象,v7 spec §11 曾据此写错限制。
- 关键词的构造方式与 steps.retrieve 一致:[product_type, *touchpoints] + 功能名。
- 一律 min_n=0 关闭补齐。否则断言可能被字母序补齐"满足",测不到打分本身——
  这是 v7 抽卡回归测试踩过的坑。
- 只用 load_frameworks()(种子库),不读 gitignore 的 .field-test/store/learned。
- **画像关键词刻意不与线索原样重合。** 初版冥想画像用过「冥想时长统计」「正念课程
  逐级解锁」,与当时拟增的线索「时长统计」「内容解锁」几乎逐字相同,SDT 65% 的分
  来自这两条——那测的是字符串抄写,不是检索语义。现版改为自然语序。
- 下面每条注释写的是**实测的命中依据**,不是望文生义的语义推断。改画像后请重算,
  别让注释和分数脱节。

## 只补了 autonomy,另两档仍是空的

给 SDT 补表层词汇有个陷阱:「好友」「一起」「同伴」各自就是一个词元,df=1 拿满
IDF,而它们在真实产品语言里极常见。补进去会让存档案例在合理改写下翻转头名
(16 个扰动翻 7 个,含「王者荣耀+好友一起开黑 → SDT」——一个靠抽卡牟利的 MOBA
被「健康内在动机」框架领衔)。把线索写长也没用:打分看共享词元,不看字符串长度,
把「同伴」写成「同伴陪伴」共享的仍是「同伴」这一个词元。故 relatedness 与
competence 一条未补,由 tests/kb/test_retrieval_perturbation.py 守住。

冥想画像因此是靠**自主性证据单档**通过的。这是已知的不完整,不是疏漏。
"""

from psyteardown.kb.loader import load_frameworks
from psyteardown.kb.retriever import retrieve_frameworks

# 记账 → fogg-behavior-model 5.427。实测命中:自动(自动导入银行账单 × ability:自动填充)
# 38%、习惯(消费习惯分析 × tag:习惯养成)26%、一键(× ability:一键操作)18%、
# 进度(储蓄目标进度 × motivation:进度激励)18%。
# 注意:Fogg 的 trigger 线索(推送通知/红点/空状态引导)一个都没命中,尽管画像里
# 有「每日记账提醒」「预算超支提示」。这条测试锁的是 ability+motivation,不是三要素齐全。
LEDGER = [
    "个人记账App", "一键记账", "账单分类标签", "预算超支提示",
    "月度消费报表", "连续记账天数", "自动导入银行账单", "账本共享",
    "消费习惯分析", "储蓄目标进度", "每日记账提醒", "年度账单总结",
]

# 待办 → flow 12.477。实测命中:任务(4 个关键词各计一次 × clear_goals:任务清单)67%、
# 清单(待办清单App × 同一条线索)17%、专注(专注计时器 × tag:专注)17%。
# 注意:分数几乎全部来自「清晰目标」这一条原则。Flow 的挑战-技能平衡(动态难度/
# 分级关卡)与即时反馈(实时校验/动效反馈)线索**零命中**。若这条测试将来变红,
# 该查的是 clear_goals 与 tag,改另外两条原则的线索不会有任何作用。
TODO = [
    "待办清单App", "快速添加任务", "完成打勾动画", "今日待办计数",
    "项目分组管理", "逾期任务标记", "周复盘总结", "重复任务设置",
    "子任务拆解", "日历视图", "专注计时器", "完成率统计",
]

# 冥想 → self-determination-theory 11.090,第二名 cognitive-biases 5.545。
# 实测命中(全部落在 autonomy,五个词元):
#   引导 2.773 25%(呼吸引导音频 + 引导语可随时跳过 × 跳过引导)
#   跳过 2.079 19%(引导语可随时跳过 × 可跳过、跳过引导)
#   免打 + 打扰 各 2.079 共 38%(夜间免打扰 × 免打扰)
#   时长 2.079 19%(每周冥想时长回顾 × 自定义时长)
# 「同伴共修房间」「好友一起冥想」「正念练习分阶解锁」三个关键词**零命中**——
# 归属与胜任两档没有表层线索,是有意为之(见模块 docstring)。画像保留它们,
# 是为了让将来补上那两档时能直接看出分数变化。
# 「呼吸引导音频」的「引导」与线索「跳过引导」属同形异义(引导音频 vs 引导流程),
# 是噪声命中,占 12.5%,不影响排序,如实记录而不刻意规避。
# 改动前 SDT 仅 2.079(只有旧线索「可跳过」命中),榜首是 cognitive-biases 与
# fogg-behavior-model 同为 5.545、前者靠库序取胜;cognitive-biases 的分全部来自
# 连续/打卡(线索「连续打卡中断警告」)与订阅(「默认订阅」),正是浅层假阳性。
MEDITATION = [
    "冥想与睡眠App", "呼吸引导音频", "睡前提醒推送", "连续冥想天数",
    "引导语可随时跳过", "正念练习分阶解锁", "情绪打卡记录", "夜间免打扰",
    "每周冥想时长回顾", "大师课付费订阅", "同伴共修房间", "好友一起冥想",
]


def _head(keywords: list[str]) -> str:
    """种子库 8 个框架里得分最高的那个。max_n=8 等于库容量,不会截断。"""
    result = retrieve_frameworks(
        load_frameworks(), keywords=keywords, max_n=8, min_n=0
    )
    assert result, "得分全零,检索返回空"
    return result[0].id


def test_ledger_app_heads_fogg():
    assert _head(LEDGER) == "fogg-behavior-model"


def test_todo_app_heads_flow():
    assert _head(TODO) == "flow"


def test_meditation_app_heads_self_determination():
    """健康类的目标态。SDT 11.09 领先 cognitive-biases 5.55。

    得分全部来自 autonomy 的三条新线索:「引导语可随时跳过」命中 跳过引导 与
    可跳过,「夜间免打扰」命中 免打扰,「每周冥想时长回顾」命中 自定义时长。
    competence 与 relatedness 一条未加——「好友」「一起」「同伴」这类单词元
    线索会让存档案例在改写下翻转,见 tests/kb/test_retrieval_perturbation.py。
    也就是说本条通过靠的是自主性证据,归属与胜任两档目前仍是空的。
    """
    assert _head(MEDITATION) == "self-determination-theory"
