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

## 冥想那条为何是 xfail:这是全库性缺陷,不是 SDT 的单点问题

曾试过给 `self-determination-theory` 补 8 条表层词汇线索(好友/一起/同伴/免打扰/
内容解锁/时长统计…),冥想画像确实变绿了。但代码评审查出它把 SDT 变成了近乎万能的
吸铁石——因为**其余 7 个框架的线索仍是设计师词汇**(难度梯度、空状态引导、默认勾选),
在真实产品描述上一律 0 分:

    直播打赏App 画像:self-determination-theory 16.6,其余 7 个框架全部 0.0
    5v5 MOBA(含抽卡)  :SDT 24.3 vs variable-ratio-reinforcement 2.1

后者是致命的:SDT 的 ethics_notes 把它定位为「健康的内在动机设计」,于是一个靠可变
比率强化牟利的产品会被报告成心理健康的产品——工具的核心判断被反转。

收窄线索无解:实测只留 3 条自主线索,仍有 4/5 个对抗画像被 SDT 登顶;按池大小归一化
也无解,因为竞争者不是「分低」而是「0 分」。**只补一个框架的词汇,就是把它变成默认
赢家。** 故已回滚(revert 50623a1),改为重开 spec 统一补全 8 个框架的表层词汇,
并配对抗画像的负向测试。

在那之前,冥想这条保持 xfail(strict):新工作落地使它转绿时,strict 会让这条测试
失败以提醒回来删掉标记。记账与待办两条不受影响,继续作为防回归锁。
"""

import pytest

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

# 冥想 → 期望 self-determination-theory,当前实测 cognitive-biases 5.545(xfail)。
# 语义上句句对应 SDT 三需求:呼吸引导可跳过(自主)、正念练习分阶解锁(胜任)、
# 好友一起冥想 / 同伴共修(归属)。但 SDT 现有线索是设计师词汇(难度梯度、非强制
# 路径、技能提升曲线),只有旧线索「可跳过」命中一次,得 2.079。
# 夺魁的 cognitive-biases 靠 连续 / 打卡(均来自线索「连续打卡中断警告」)与
# 订阅(来自「默认订阅」)三个零碎通用词元——正是 v7 一路在打的浅层假阳性。
# 它与 fogg-behavior-model 其实同为 5.545,靠库序取胜。
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


@pytest.mark.xfail(
    strict=True,
    reason="知识库整体使用设计师词汇,对真实产品语言覆盖极差;"
           "只补 SDT 一个框架会使它变成万能吸铁石(见模块 docstring)。"
           "待 8 个框架统一补全表层词汇后转绿,届时请删掉本标记。",
)
def test_meditation_app_heads_self_determination():
    """健康类的目标态,当前未达成。

    这条不是「将来某天也许会修」的许愿池:它锁定的是一个已经定位到根因、
    已有明确修法、只是修法范围超出上一份 spec 的缺陷。strict=True 保证它
    一旦转绿就会失败,不会悄悄躺成永久豁免。
    """
    assert _head(MEDITATION) == "self-determination-theory"
