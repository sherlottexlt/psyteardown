"""非游戏品类的检索覆盖:三个验证画像的头名框架必须语义正确。

设计要点(改动前请先读):
- 画像各 12 个关键词,匹配 step1 真实产出的丰度(实测既有 6 案例为 12~19 词)。
  用 3 个关键词的稀疏画像测出的"零覆盖"是假象,v7 spec §11 曾据此写错限制。
- 关键词的构造方式与 steps.retrieve 一致:[product_type, *touchpoints] + 功能名。
- 一律 min_n=0 关闭补齐。否则断言可能被字母序补齐"满足",测不到打分本身——
  这是 v7 抽卡回归测试踩过的坑。
- 只用 load_frameworks()(种子库),不读 gitignore 的 .field-test/store/learned。
"""

from psyteardown.kb.loader import load_frameworks
from psyteardown.kb.retriever import retrieve_frameworks

# 记账:一键记账降摩擦 + 连续天数触发,是 Fogg 行为模型的动机/能力/提示三要素
LEDGER = [
    "个人记账App", "一键记账", "账单分类标签", "预算超支提示",
    "月度消费报表", "连续记账天数", "自动导入银行账单", "账本共享",
    "消费习惯分析", "储蓄目标进度", "每日记账提醒", "年度账单总结",
]

# 待办:专注计时器 + 子任务拆解 + 完成反馈,是 Flow 的挑战/技能平衡与即时反馈
TODO = [
    "待办清单App", "快速添加任务", "完成打勾动画", "今日待办计数",
    "项目分组管理", "逾期任务标记", "周复盘总结", "重复任务设置",
    "子任务拆解", "日历视图", "专注计时器", "完成率统计",
]

# 冥想:自选内容/跳过引导(自主)+ 逐级解锁(胜任)+ 好友一起(归属),即 SDT 三需求
MEDITATION = [
    "冥想与睡眠App", "呼吸引导音频", "睡前提醒推送", "连续冥想天数",
    "正念课程逐级解锁", "情绪打卡记录", "白噪音音效库", "冥想时长统计",
    "大师课付费订阅", "睡眠质量报告", "成就徽章", "好友一起冥想",
]


def _head(keywords: list[str]) -> str:
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
    """本次要修的一条:改动前 SDT 得 0.0 分,由 cognitive-biases 靠
    连续/打卡/订阅三个零碎通用词元夺魁——正是浅层假阳性。"""
    assert _head(MEDITATION) == "self-determination-theory"
