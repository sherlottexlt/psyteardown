"""扰动护栏:存档画像加一个合理的同义改写关键词后,头名框架不得翻转。

为什么需要这条:spec 原本的护栏是「6 个存档案例的头名一个都不变」,但那是拿
**冻结的措辞**在比。step1 是 LLM,同一产品重跑一次措辞就会变;而多邻国的头名
领先只有 1.39 分,一个含「好友」的关键词就值 2.08 分。冻结文本能过,不等于
这个头名是稳定的。

本模块的历史价值:它否掉了本任务的第一版实现(SDT 补 8 条线索)。那版 16 个扰动
翻转 7 个,包括「王者荣耀 + 好友一起开黑 → SDT」——一个靠抽卡牟利的 MOBA 被
「健康内在动机」框架领衔。冻结文本的护栏完全没看出来。

依赖 .field-test/store/cases.db(在 gitignore 内),故无库时跳过。
"""

import json
import sqlite3
from pathlib import Path

import pytest

from psyteardown.kb.loader import load_frameworks
from psyteardown.kb.retriever import retrieve_frameworks

_CASES_DB = Path(".field-test/store/cases.db")

# (案例名, 追加的关键词)。全部取自「该产品本来就有这个功能、只是换个说法」:
# 王者荣耀存档含「组队开黑与亲密关系」,多邻国含「家庭套餐与好友动态」,
# Keep 含训练计划,拼多多含拼团。这些不是编造的边缘情况。
PERTURBATIONS = [
    ("王者荣耀", "好友一起开黑"),
    ("王者荣耀", "战队同伴"),
    ("王者荣耀", "使用时长统计"),
    ("多邻国", "好友一起学习"),
    ("多邻国", "课程内容解锁"),
    ("多邻国", "每日学习时长"),
    ("Keep", "好友一起打卡"),
    ("Keep", "训练内容解锁"),
    ("小红书 (RED)", "好友一起逛"),
    ("小红书 (RED)", "免打扰模式"),
    ("拼多多", "好友一起拼单"),
    ("拼多多", "同伴助力"),
    ("金铲铲之战", "好友一起上分"),
    ("金铲铲之战", "对局时长统计"),
]

# 基线本就存在的翻转,不因本次改动而起,故列为已知例外而非放宽断言。
# 王者荣耀加「新手引导可跳过」会命中 SDT 的**原有**线索「可跳过」而翻转。
# 这一处争议不大:一个 MOBA 因为新手引导可跳过就被 SDT 领衔并不合理,
# 但它是 v7 遗留问题,修它要动 cialdini/SDT 的相对权重,超出本次范围。
KNOWN_BASELINE_FLIPS = {("王者荣耀", "新手引导可跳过")}


def _profiles() -> dict[str, list[str]]:
    conn = sqlite3.connect(_CASES_DB)
    rows = list(conn.execute("SELECT product_name, case_json FROM cases"))
    conn.close()
    out = {}
    for name, case_json in rows:
        product = json.loads(case_json)["result"]["product"]
        # 与 steps.retrieve 构造关键词的方式保持一致
        keywords = [product["product_type"], *product["touchpoints"]]
        keywords += [f["name"] for f in product["features"]]
        out[name] = keywords
    return out


def _head(keywords: list[str]) -> str:
    result = retrieve_frameworks(
        load_frameworks(), keywords=keywords, max_n=8, min_n=0
    )
    assert result, "得分全零,检索返回空"
    return result[0].id


@pytest.mark.skipif(not _CASES_DB.exists(), reason="cases.db 在 gitignore 内,仅本地可跑")
@pytest.mark.parametrize("name,extra", PERTURBATIONS)
def test_head_survives_plausible_rewording(name, extra):
    profiles = _profiles()
    assert name in profiles, f"存档里没有 {name},请更新 PERTURBATIONS"
    baseline = _head(profiles[name])
    perturbed = _head(profiles[name] + [extra])
    assert perturbed == baseline, (
        f"{name} 追加「{extra}」后头名由 {baseline} 翻为 {perturbed}。"
        f"若这是新增线索导致的,应收回线索而非放宽本断言。"
    )


@pytest.mark.skipif(not _CASES_DB.exists(), reason="cases.db 在 gitignore 内,仅本地可跑")
def test_known_baseline_flip_is_still_only_one():
    """已知例外必须保持是「已知」的:若它自己消失了,说明有人改动了原有线索,
    该来删掉这条豁免;若又冒出新的基线翻转,本测试也会失败。"""
    profiles = _profiles()
    flips = set()
    for name, extra in KNOWN_BASELINE_FLIPS:
        if _head(profiles[name] + [extra]) != _head(profiles[name]):
            flips.add((name, extra))
    assert flips == KNOWN_BASELINE_FLIPS, (
        f"已知基线翻转集合发生变化:实际 {flips},预期 {KNOWN_BASELINE_FLIPS}"
    )
