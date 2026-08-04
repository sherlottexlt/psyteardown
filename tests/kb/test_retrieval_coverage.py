"""非游戏品类的检索覆盖:三个验证画像的头名框架必须语义正确。

设计要点(改动前请先读):
- 画像各 12 个关键词,匹配 step1 真实产出的丰度(实测既有 6 案例为 12~19 词)。
  用 3 个关键词的稀疏画像测出的"零覆盖"是假象,v7 spec §11 曾据此写错限制。
- 关键词的构造方式与 steps.retrieve 一致:[product_type, *touchpoints] + 功能名。
- 一律 min_n=0 关闭补齐。否则断言可能被字母序补齐"满足",测不到打分本身——
  这是 v7 抽卡回归测试踩过的坑。
- 只用 load_frameworks()(种子库),不读 gitignore 的 .field-test/store/learned。
- **画像关键词刻意不与线索原样重合。** 初版冥想画像用过「冥想时长统计」「正念课程
  逐级解锁」,与线索「时长统计」「内容解锁」几乎逐字相同,SDT 65% 的分来自这两条:
  同时去掉它们,SDT 与 cognitive-biases 打成 5.5452 平手并因库序落败。那样测的是
  字符串抄写,不是检索语义。现版改为自然语序,任意去掉 3 个关键词 SDT 仍居首
  (穷举 0/220 组合失守),最大单个词元仅占 14%。
- 下面每条注释写的是**实测的命中依据**,不是望文生义的语义推断。改画像后请重算,
  别让注释和分数脱节。
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

# 冥想 → self-determination-theory 19.408,证据分散在三种需求上,无单点依赖:
#   自主 48%:引导/跳过(引导语可随时跳过 × autonomy:跳过引导、可跳过)、
#            免打/打扰(夜间免打扰 × autonomy:免打扰)、时长(× autonomy:自定义时长)
#   胜任 11%:解锁(正念练习分阶解锁 × competence:内容解锁)
#   归属 32%:同伴(同伴共修房间)、好友 + 一起(好友一起冥想)
# 「呼吸引导音频」的「引导」与线索「跳过引导」是同形异义(引导音频 vs 引导流程),
# 属噪声命中,但仅占 7% 且不影响排序,如实记录而不刻意规避。
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
    """本次要修的一条:改动前 SDT 仅得 2.079(唯一命中来自旧线索「可跳过」),
    由 cognitive-biases 以 5.545 夺魁——靠连续/打卡/订阅三个零碎通用词元,
    正是浅层假阳性。"""
    assert _head(MEDITATION) == "self-determination-theory"
