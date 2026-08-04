# 非游戏品类线索覆盖 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让冥想/睡眠类产品画像检索到 `self-determination-theory` 作为头名框架,且不使任何既有案例在合理改写下翻转头名。

**Architecture:** 不动检索算法、不动 schema、不新增框架。只给 `self-determination-theory` 的 `autonomy` 原则补 3 条表层词汇线索,并用「验证画像 + 扰动护栏」两类测试锁定。

**Tech Stack:** Python 3.12 / pydantic / pytest。KB 为 `src/psyteardown/data/frameworks/*.yaml`,检索为 `src/psyteardown/kb/retriever.py`(本次不改)。

**Baseline(本计划起点,已在分支上):** `230 passed, 2 skipped, 1 xfailed`。分支 `kb/nongame-clue-coverage`,HEAD `c5bd54c`。

---

## 这份计划被推翻重写过一次,先读这一节

本文件的前一版让 SDT 补 8 条线索(competence 加 `内容解锁`/`时长统计`,relatedness 加
`好友`/`一起`/`同伴`)。那版**实现过、全绿过、提交过**(`a1bc032`),随后回滚
(`50623a1`)。回滚理由与两条必须记住的教训:

### 回滚理由:真实存档画像在合理改写下翻转头名

| 线索集 | 16 个扰动中翻转 | 冥想画像头名 |
|--------|----------------|-------------|
| 不加(基线) | 1 | `cognitive-biases` 5.55 ✗ |
| **本计划的 3 条** | **2** | **SDT 11.09,领先 5.55** ✓ |
| 已回滚的 8 条 | 7 | SDT 19.41 ✓ |

被翻转的都是真实存档画像加一个合理同义改写:

```
王者荣耀 + [好友一起开黑]   cialdini-influence  → SDT
多邻国   + [好友一起学习]   fogg-behavior-model → SDT
多邻国   + [课程内容解锁]   fogg-behavior-model → SDT
王者荣耀 + [使用时长统计]   cialdini-influence  → SDT
```

王者荣耀的存档画像本就含「组队开黑与亲密关系」,多邻国本就含「家庭套餐与好友动态」
——只差一个同义词。而 step1 是 LLM,同一产品重跑一次措辞就会变。多邻国的头名领先仅
1.39,一个含 `好友` 的关键词值 2.08。

### 教训一:线索写长并不能降低风险

打分看的是共享**词元**,不是线索字符串长度。把 `同伴` 写成 `同伴陪伴`,共享的仍是
`同伴` 这一个词元,权重分毫不变。唯一有效的办法是**让这些词元根本不进入词元池**。
所以 relatedness 一条都不加,不是"暂时不加",是"加不了"。

### 教训二:用手写的对抗画像下结论,会得出错误结论

回滚过程中我一度断言「SDT 成了万能吸铁石,其余 7 个框架在真实产品语言上一律 0 分」。
那是用**我自己照着 SDT 线索写的 6 词薄画像**测出来的。换成 12~14 词、按存档案例风格
写的真实画像重测,8 条线索**什么都没改变**:

| 画像 | 不加线索 | 加 8 条线索 |
|------|---------|------------|
| 抖音-like | `hook-model` 15.25 | `hook-model` 15.25 |
| 直播打赏 | `cialdini-influence` 6.24 | `cialdini-influence` 6.24 |
| MOBA | `flow` 6.12 | `flow` 6.12 |

其余框架的线索(`推送通知`/`红点`/`限时`/`倒计时`/`划线原价`/`热门榜`)本来就是表层
词汇,非零 6/8。**下结论前,画像必须按真实丰度写,且不得照着线索表编。**

---

## File Structure

| 文件 | 责任 | 动作 |
|------|------|------|
| `src/psyteardown/data/frameworks/self-determination-theory.yaml` | SDT 框架定义,只改 `autonomy.look_for` | 修改 |
| `tests/kb/test_retrieval_coverage.py` | 三个验证画像的头名锁定(已存在,需去掉 xfail) | 修改 |
| `tests/kb/test_retrieval_perturbation.py` | 扰动护栏:存档画像加一个合理关键词后头名不得翻转 | 新建 |
| `docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md` | v7 spec §11 第一条数据错误 | 修改 |
| `docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md` | 本次 spec,§3~§5 需按实际收敛结果订正 | 修改 |

`retriever.py` / `models.py` / `steps.py` / `orchestrator.py` 一律不动。

---

## Task 1: 扰动护栏(先写,红)

**Files:**
- Create: `tests/kb/test_retrieval_perturbation.py`

先写护栏再改 KB。护栏此刻应当**通过**(基线只有 1 处翻转,已列为已知例外),改完 KB
后必须仍然通过——它的作用是接住 Task 2,不是接住现状。

- [ ] **Step 1: 写护栏测试**

新建 `tests/kb/test_retrieval_perturbation.py`,完整内容:

```python
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
```

- [ ] **Step 2: 运行,确认此刻全绿**

```bash
python -m pytest tests/kb/test_retrieval_perturbation.py -v
```

Expected: **15 passed**(14 条参数化 + 1 条已知例外校验),无 skip。

若显示 SKIPPED,说明工作目录不是仓库根。从仓库根运行,不要删 skipif。

全量应为 `245 passed, 2 skipped, 1 xfailed`(起点 230 passed + 15 新增)。

- [ ] **Step 3: 提交**

```bash
git add tests/kb/test_retrieval_perturbation.py
git commit -m "test(kb): 扰动护栏 — 存档画像加一个合理改写词后头名不得翻转"
```

---

## Task 2: 补入 3 条自主线索(绿)

**Files:**
- Modify: `src/psyteardown/data/frameworks/self-determination-theory.yaml`
- Modify: `tests/kb/test_retrieval_coverage.py`(去掉 xfail 标记)

- [ ] **Step 1: 改 YAML**

只改 `autonomy` 一条原则的 `look_for`,追加 3 项。**`competence` 与 `relatedness`
一个字都不动**:

```yaml
principles:
  - id: autonomy
    name: 自主(Autonomy)
    description: 用户感到行为出于自己的选择。
    look_for: [可自定义, 可跳过, 非强制路径, 跳过引导, 免打扰, 自定义时长]
  - id: competence
    name: 胜任(Competence)
    description: 用户感到自己在进步、能掌控。
    look_for: [难度梯度, 即时反馈, 技能提升曲线]
  - id: relatedness
    name: 归属(Relatedness)
    description: 用户感到与他人连接。
    look_for: [社区, 协作, 互助, 关系绑定]
```

**不得补入下列任何一条**,它们都进过早期版本、都被扰动护栏或"只在 SDT 不该领衔的
画像上加分"这条标准剔除:

| 曾拟增 | 剔除理由 |
|--------|---------|
| `好友` / `一起` / `同伴` | 各是单个词元、df=1 拿满 IDF 2.079,而在真实产品语言里极常见。7/16 扰动翻转的主因 |
| `内容解锁` / `时长统计` | 使「多邻国+课程内容解锁」「王者荣耀+使用时长统计」翻转;且 `内容解锁` 匹配付费墙不亚于匹配进度 |
| `课程解锁` | 引入词元 `课程`,撞上多邻国触点「课程完成结算页」,直接翻转两个存档案例 |
| `自选内容` / `逐级进阶` / `关卡` | 验证画像一条都不命中,无从证明其必要 |
| `组队` / `分享给朋友` / `完成率` | 只在 SDT 不该领衔的画像上加分 |

- [ ] **Step 2: 去掉 xfail 标记**

在 `tests/kb/test_retrieval_coverage.py` 中删除 `test_meditation_app_heads_self_determination`
上方的整个 `@pytest.mark.xfail(...)` 装饰器(4 行),并把该测试的 docstring 换成:

```python
def test_meditation_app_heads_self_determination():
    """健康类的目标态。SDT 11.09 领先 cognitive-biases 5.55。

    得分全部来自 autonomy 的三条新线索:引导语可随时跳过 命中 跳过引导 与
    可跳过,夜间免打扰 命中 免打扰,每周冥想时长回顾 命中 自定义时长。
    competence 与 relatedness 一条未加——「好友」「一起」「同伴」这类单词元
    线索会让存档案例在改写下翻转,见 tests/kb/test_retrieval_perturbation.py。
    也就是说本条通过靠的是自主性证据,归属与胜任两档目前仍是空的。
    """
    assert _head(MEDITATION) == "self-determination-theory"
```

同时把模块 docstring 里那一整节「## 冥想那条为何是 xfail」删掉,换成:

```
## 只补了 autonomy,另两档仍是空的

给 SDT 补表层词汇有个陷阱:「好友」「一起」「同伴」各自就是一个词元,df=1 拿满
IDF,而它们在真实产品语言里极常见。补进去会让存档案例在合理改写下翻转头名
(16 个扰动翻 7 个,含「王者荣耀+好友一起开黑 → SDT」)。把线索写长也没用——
打分看共享词元,不看字符串长度。故 relatedness 与 competence 一条未补。

冥想画像因此是靠**自主性证据单档**通过的。这是已知的不完整,不是疏漏。
```

- [ ] **Step 3: 跑三层测试**

```bash
python -m pytest tests/kb/test_retrieval_coverage.py tests/kb/test_retrieval_perturbation.py -v
```

Expected: **18 passed**(3 覆盖 + 15 扰动),**0 xfailed**。

冥想头名 `self-determination-theory` 11.09,第二名 `cognitive-biases` 5.545。

若扰动护栏出现失败,**收回线索,不要放宽护栏**。

- [ ] **Step 4: 全量**

```bash
python -m pytest -q
```

Expected: `246 passed, 2 skipped`(Task 1 后的 245 passed + xfail 转 pass)。

`test_gacha_keywords_retrieve_variable_ratio_first` 必须仍然通过。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/data/frameworks/self-determination-theory.yaml tests/kb/test_retrieval_coverage.py
git commit -m "feat(kb): SDT 自主线索补 3 条表层词汇,冥想画像头名转正"
```

---

## Task 3: 两处 spec 订正

**Files:**
- Modify: `docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md`
- Modify: `docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md`

- [ ] **Step 1: 重写 v7 spec §11 第一条**

在 `2026-08-03-v7-framework-retrieval-design.md` 的 `### 一、无命中时仍退回字母序`
一节中,把从「实测(仅种子库 8 个框架):」到「…理财、工具类产品在当前知识库下仍会
落回字母序。」整段替换为:

```markdown
> ⚠️ **本节原实测数据有误,已于 2026-08-04 更正。** 原表用的画像只有 3 个关键词
> (`记账App / 每日提醒 / 账单分类`),而 step1 产出的真实画像有 12~19 个关键词
> (实测 6 案例:小红书 12、多邻国 12、拼多多 13、Keep 13、王者荣耀 13、金铲铲 19)。
> 稀疏画像放大了零覆盖的程度。详见 `2026-08-04-nongame-clue-coverage-design.md`。

实测(仅种子库 8 个框架,画像按真实丰度取 12~14 词):

| 产品画像 | 非零框架数 | 头名 | 语义判定 |
|---------|-----------|------|---------|
| 记账 App | 6 / 8 | `fogg-behavior-model` | ✓ |
| 待办清单 App | 6 / 8 | `flow` | ✓ |
| 冥想睡眠 App | 6 / 8 | `self-determination-theory` | ✓(2026-08-04 补线索后) |
| 抖音-like | 6 / 8 | `hook-model` | ✓ |
| 金铲铲 | 8 / 12 | `variable-ratio-reinforcement` | ✓ |

**结论要说准确:字母序补齐这条限制在机制上依然存在**——补齐循环按 `library` 顺序
遍历,而 `load_frameworks` 按 `id` 排序。但它的实际触发面比原文写的窄得多:按真实
画像丰度,非游戏品类也有 6/8 个非零框架,并不会整体落回字母序。
```

同时把该节最后一段的「后续方向」改为:

```markdown
这不比修复前更差,但**不应把 v7 描述为"检索问题已解决"**。字母序补齐仅在关键词与
全部框架零交集时才暴露(实测需画像极稀疏),优先级因此下调。知识库线索覆盖已于
2026-08-04 部分处理(仅 SDT 的 autonomy),其余框架与其余原则仍是设计师词汇。
```

- [ ] **Step 2: 在本次 spec 追加「实际收敛结果」一节**

在 `2026-08-04-nongame-clue-coverage-design.md` 末尾追加:

```markdown
---

## 8. 实际收敛结果(实现后回填,与 §4 原案有出入)

§4 原本计划给三条原则各补 4~5 条表层线索(共 14 条)。**实际只落地 3 条,全部在
`autonomy`。** 收敛过程与原因:

| 轮次 | 线索数 | 被否原因 |
|------|--------|---------|
| 原案 | 14 | `课程解锁` 引入词元 `课程`,直接翻转多邻国与 Keep |
| 二轮 | 9 → 8 | 无验证画像命中者、只在 SDT 不该领衔的画像上加分者,逐条剔除 |
| 三轮 | 8 → **3** | 扰动护栏:8 条版本在 16 个合理改写扰动中翻转 7 个 |

**根因:`好友`/`一起`/`同伴` 各自就是一个词元,df=1 拿满 IDF,而在真实产品语言里
极常见。** 把线索写长无效——打分看共享词元,不看字符串长度。故 `relatedness` 与
`competence` 一条未补,冥想画像是靠自主性单档通过的。

### 对 §3「现有 6 个案例头名一个都不改变」这条护栏的修正意见

该护栏拿**冻结的措辞**在比,不足以保证稳定性:多邻国头名领先仅 1.39,一个含 `好友`
的关键词值 2.08。8 条版本完全通过了这条护栏,却在改写下翻转 7 处。已由
`tests/kb/test_retrieval_perturbation.py` 补强为「加一个合理改写词后仍不翻转」。

另记一条**未采纳的反对意见**:多邻国是 SDT 的教科书案例,Keep 由 SDT 领衔也比
`cognitive-biases` 站得住。该护栏把修复前的头名当成了基准真值,而那些头名恰是本次
要修的浅层匹配产出的。本次仍按已批准标准执行(它能防止无约束漂移),但该护栏本身
是否合理值得单独讨论。

### 一条方法论教训

回滚 8 条版本的过程中,曾用**照着线索表手写的 6 词薄画像**得出「SDT 成了万能吸铁石、
其余框架在真实产品语言上一律 0 分」的结论。换成按存档案例风格写的 12~14 词真实画像
重测,8 条线索对抖音/直播打赏/MOBA 三个画像**什么都没改变**(头名与非零数全同)。
**下结论前,画像必须按真实丰度写,且不得照着线索表编。**
```

- [ ] **Step 3: 跑全量确认文档改动没碰代码,并提交**

```bash
python -m pytest -q
```

Expected: `232 passed, 2 skipped`。

```bash
git add docs/superpowers/specs/
git commit -m "docs: 订正 v7 spec §11 稀疏画像数据,回填本次实际收敛结果"
```

---

## Task 4: 收尾核对

- [ ] **Step 1: 核对 spec §3 的四条成功标准**

```bash
python -m pytest tests/kb/ -v
```

1. 三个验证画像头名语义正确 → `test_retrieval_coverage.py` 3 条 PASS,**无 xfail**
2. 现有 6 案例头名不变,且在合理改写下仍不变 → `test_retrieval_perturbation.py` 15 条 PASS
3. 抽卡回归 → `test_gacha_keywords_retrieve_variable_ratio_first` PASS
4. IDF 稀释可控 → 见 Step 2

- [ ] **Step 2: 记录 df 分布**

```bash
python - <<'PY'
import sys; sys.path.insert(0, 'src')
import math
from psyteardown.kb.loader import load_frameworks
from psyteardown.kb.retriever import _pool
pools = [_pool(f) for f in load_frameworks()]
df = {}
for p in pools:
    for t in p: df[t] = df.get(t, 0) + 1
hist = {}
for v in df.values(): hist[v] = hist.get(v, 0) + 1
print(f'N={len(pools)} 词元={len(df)} df直方图={dict(sorted(hist.items()))}')
print(f'IDF 区间 {math.log(len(pools)/max(df.values())):.3f}~{math.log(len(pools)/1):.3f}')
PY
```

预期词元数在 403(改前)与 415(8 条版本)之间;只补 3 条,预期约 409。
把实测值填进本次 spec 第 8 节。**若与预期差距大,先查清原因再继续。**

- [ ] **Step 3: 核对非目标未越界**

```bash
git diff 7cfc391..HEAD --stat -- src/
```

Expected: 只有 `src/psyteardown/data/frameworks/self-determination-theory.yaml`。
`retriever.py`/`models.py`/`steps.py`/`orchestrator.py` 或其他 YAML 出现即为越界。

- [ ] **Step 4: 报告**

必须说明:本次**没有**跑真实 LLM 端到端拆解,只验证了检索层的头名。要看端到端
效果需另跑一次真实拆解,不在本计划内。

---

## Self-Review

**Spec 覆盖:**

| spec 章节 | 落点 |
|-----------|------|
| §1 更正 v7 §11 | Task 3 Step 1 |
| §3 标准 1(三画像头名正确) | Task 2 Step 3 |
| §3 标准 2(6 案例头名不变) | Task 1 + Task 2 Step 3(已强化为扰动护栏) |
| §3 标准 3(抽卡回归) | Task 2 Step 4、Task 4 Step 1 |
| §3 标准 4(IDF 稀释可控) | Task 4 Step 2 |
| §3 非目标 | Task 4 Step 3 显式核验 |
| §4 改动 | Task 2 Step 1(仅 3 条,出入记于 Task 3 Step 2) |
| §7 附带修正 | Task 3 Step 1 |

**占位符扫描:** 无 TBD;每个改代码的步骤都给了完整代码与预期输出。

**测试计数:** 起点 `230 passed, 2 skipped, 1 xfailed`(共 233 条)
→ Task 1 加 15 条 → `245 passed, 2 skipped, 1 xfailed`
→ Task 2 把 xfail 转 pass → `246 passed, 2 skipped`。
(初稿这里算错过一次,写成 232;已按上式改正,Task 1 Step 2 与 Task 2 Step 4 的
Expected 已同步。实现时以实际输出为准,不符先查原因再继续。)
