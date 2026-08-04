# 非游戏品类线索覆盖 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让工具类与健康类产品画像检索到语义正确的头名框架,方式是给 `self-determination-theory` 补入表层词汇线索,并用验证画像测试锁定。

**Architecture:** 不动检索算法。只改一个 YAML 的 `look_for`,加一个新测试模块。先写验证画像测试(红),再补线索(绿)——顺序倒过来做,避免凭空发明线索。三个画像各 12 词,匹配真实画像丰度;一律 `min_n=0` 关闭字母序补齐,使断言纯粹反映打分。

**Tech Stack:** Python 3.12 / pydantic / pytest。KB 为 `src/psyteardown/data/frameworks/*.yaml`,检索为 `src/psyteardown/kb/retriever.py`(本次不改)。

**Baseline:** `228 passed, 2 skipped`(`python -m pytest -q`)。HEAD = `7cfc391`,分支 `main`。

---

## 前置:实现前必读的两条实测结论

写这份计划时已把改动跑过一遍,有两处与 spec 不同,**实现时按本计划、不按 spec 原文**:

### 一、spec §4 列出的「课程解锁」必须收回,改写为「内容解锁」

spec §4 的增补表里有一条 `课程解锁`。实测它是唯一会破坏硬性护栏的线索:它引入词元 `课程`,而 DB 中多邻国的触点含「课程完成结算页」、Keep 的功能含「课程」,于是两个既有案例的头名双双翻到 `self-determination-theory`:

```
多邻国:  fogg-behavior-model → self-determination-theory
Keep:   cognitive-biases    → self-determination-theory
```

spec §5 已经预先规定了处置方式:「若某条增补线索使既有案例头名翻转,该线索应被收回而非调整期望值。」

逐条剔除实验证明它是**唯一**的肇因(其余线索全留、只去掉这一条即全绿),且改写为不含 `课程` 的同义写法(`内容解锁` / `逐级解锁` / `章节解锁` / `进度解锁`)同样全绿。故取 `内容解锁`:保住「解锁」这个语义,避开 `课程` 这个碰撞词元。冥想画像仍达标,`课程解锁` 原本贡献的 `解锁` 由 `内容解锁` 原样接住。

### 二、那两个翻转「可能是变好了,不是变坏了」——须如实记录,但本次不据此放宽护栏

多邻国是 SDT 的教科书案例,Keep 由 SDT 领衔也比 `cognitive-biases` 更站得住。也就是说,spec §3 那条「现有 6 个案例头名一个都不改变」的护栏,**把修复前的头名当成了基准真值,而那些头名恰是本次要修的浅层匹配产出的**。

本次仍遵守该护栏(它是已批准的验收标准,且能防止无约束漂移),但 Task 5 要把这个观察写进 spec,留给后续决定。**不要在实现中自行放宽护栏或改期望值。**

### 三、冥想画像与线索表都已按代码评审重做过一轮

Task 1 首次实现后,代码质量评审提出一条 Critical:冥想画像里的「冥想时长统计」
「正念课程逐级解锁」与拟增线索「时长统计」「内容解锁」几乎逐字相同,SDT 65% 的分来自
这两条;同时去掉它们,SDT 与 `cognitive-biases` 打成 5.5452 平手并因库序落败。**那样
测的是字符串抄写,不是检索语义**——画像与线索是闭环共同设计出来的,测试无法独立佐证
"SDT 适合冥想类产品"这个结论。评审同时指出三条画像注释写的语义理由与实际命中的词元
对不上(例:记账那条声称命中 Fogg 的 trigger 三要素,实测 trigger 线索零命中)。

两条都成立,已在本计划中修掉:

- 冥想画像改为自然语序、不与线索原样重合,证据分散到三种需求上。穷举验证:任意去掉
  **3 个**关键词,SDT 仍居首(0/220 组合失守),最大单个词元占比从 39% 降到 14%。
- 三条画像注释改为**实测命中依据**(词元、来源线索、占比),并显式写出"哪些线索没有
  命中",避免将来有人照着错注释去改错原则。
- 线索表从 13 条压到 **9 条**:`自选内容`/`逐级进阶`/`关卡`/`组队`/`分享给朋友` 无任何
  验证画像命中,其中 `组队` 只在王者荣耀触发、`分享给朋友` 只在拼多多与 Keep 触发——
  恰是 SDT 不该领衔的案例。

**下面 Task 1 与 Task 2 给出的内容已是修正版,直接照做即可。**

---

## File Structure

| 文件 | 责任 | 动作 |
|------|------|------|
| `tests/kb/test_retrieval_coverage.py` | 三个非游戏验证画像的头名锁定 + 既有案例不回归的护栏说明 | 新建 |
| `src/psyteardown/data/frameworks/self-determination-theory.yaml` | SDT 框架定义,本次只改 `look_for` | 修改 |
| `docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md` | v7 spec,§11 第一条限制数据错误 | 修改 |
| `docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md` | 本次 spec,§4 需记录「课程解锁」的收回 | 修改 |

不新建源文件。`retriever.py` / `models.py` / `steps.py` / `orchestrator.py` 一律不动。

---

## Task 1: 验证画像测试模块(红)

**Files:**
- Create: `tests/kb/test_retrieval_coverage.py`

- [ ] **Step 1: 写三条失败测试**

新建 `tests/kb/test_retrieval_coverage.py`,完整内容:

```python
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
```

- [ ] **Step 2: 运行,确认两绿一红**

```bash
python -m pytest tests/kb/test_retrieval_coverage.py -v
```

Expected:
- `test_ledger_app_heads_fogg` PASS(记账画像本就正确,这条是防回归锁)
- `test_todo_app_heads_flow` PASS(同上)
- `test_meditation_app_heads_self_determination` **FAIL**,断言消息形如
  `AssertionError: assert 'cognitive-biases' == 'self-determination-theory'`

若冥想那条意外通过,停下来——说明 KB 已被改过,本计划的前提不成立。

- [ ] **Step 3: 提交红测试**

```bash
git add tests/kb/test_retrieval_coverage.py
git commit -m "test(kb): 非游戏品类验证画像 — 冥想 App 头名当前不正确(红)"
```

---

## Task 2: 补入 SDT 表层线索(绿)

**Files:**
- Modify: `src/psyteardown/data/frameworks/self-determination-theory.yaml`
- Test: `tests/kb/test_retrieval_coverage.py`

改动理由:线索写成了设计师术语(难度梯度、非强制路径),产品画像说的是用户可见的表层话(内容解锁、好友、跳过)。字符 n-gram 跨不过这种词汇层级差。**保留原抽象词,并列补入表层同义变体。**

- [ ] **Step 1: 改 YAML**

把 `principles` 三条的 `look_for` 改成下面这样(其余字段 `id`/`name`/`category`/`summary`/`tags`/`references`/`ethics_notes` 全部不动):

```yaml
principles:
  - id: autonomy
    name: 自主(Autonomy)
    description: 用户感到行为出于自己的选择。
    look_for: [可自定义, 可跳过, 非强制路径, 跳过引导, 免打扰, 自定义时长]
  - id: competence
    name: 胜任(Competence)
    description: 用户感到自己在进步、能掌控。
    look_for: [难度梯度, 即时反馈, 技能提升曲线, 内容解锁, 完成率, 时长统计]
  - id: relatedness
    name: 归属(Relatedness)
    description: 用户感到与他人连接。
    look_for: [社区, 协作, 互助, 关系绑定, 好友, 一起, 同伴]
```

共 **9 条**新线索(三条原则各 3 条)。每条都被 Task 1 的验证画像实际命中——没有一条是
无测试佐证的臆想词汇。

**两条硬性用词约束,改动前必读:**

1. **「内容解锁」不得写成「课程解锁」**——它引入词元 `课程`,撞上多邻国的触点
   「课程完成结算页」,会让 Task 3 的既有案例护栏失败。理由见本文件开头「前置」第一条。
2. **不要再补 `自选内容` / `逐级进阶` / `关卡` / `组队` / `分享给朋友` 这 5 条。**
   它们是计划初版的一部分,后被剔除:三个验证画像**一条都不命中**它们,故无从证明其
   必要;而 `组队` 只在王者荣耀上触发、`分享给朋友` 只在拼多多与 Keep 上触发——恰是
   SDT **不该**领衔的三个案例,纯属把噪声推向 SDT。删掉后全库词元从 426 降到 416,
   三个画像与六个案例的判定一字不变。

- [ ] **Step 2: 运行三条测试,确认全绿**

```bash
python -m pytest tests/kb/test_retrieval_coverage.py -v
```

Expected: 3 passed。冥想画像头名变为 `self-determination-theory`(分数 19.408,非零 7/8,
第二名 `cognitive-biases` 5.545,领先 71%)。

- [ ] **Step 3: 跑全量,确认无回归**

```bash
python -m pytest -q
```

Expected: `231 passed, 2 skipped`(基线 228 + 新增 3)。

若 `tests/kb/test_retriever.py::test_gacha_keywords_retrieve_variable_ratio_first` 失败,说明新线索污染了抽卡检索——停下来报告,不要改那条测试。

- [ ] **Step 4: 提交**

```bash
git add src/psyteardown/data/frameworks/self-determination-theory.yaml
git commit -m "feat(kb): SDT 线索补入表层同义词,修正健康类头名框架"
```

---

## Task 3: 既有案例头名护栏(硬性)

**Files:**
- Test: `tests/kb/test_retrieval_coverage.py`(追加)

spec §3 第 2 条与 §5 都把「现有 6 个案例头名一个都不改变」列为硬性。这条不能只靠人工跑脚本确认,但也**不能写成单元测试**——`.field-test/store/cases.db` 在 gitignore 内,测试依赖它会在干净检出上失败。

处置:写一个显式跳过的护栏测试,把复现命令与已知结论写在里面。这样结论有归档、命令可复用,又不会让 CI 依赖不存在的文件。

- [ ] **Step 1: 追加护栏测试**

在 `tests/kb/test_retrieval_coverage.py` 末尾追加:

```python
import json
import sqlite3
from pathlib import Path

import pytest

_CASES_DB = Path(".field-test/store/cases.db")


@pytest.mark.skipif(not _CASES_DB.exists(), reason="cases.db 在 gitignore 内,仅本地可跑")
def test_existing_cases_keep_their_head_framework():
    """硬性护栏:补线索不得改变既有案例的头名框架。

    已知结论(实现时实测):9 条线索全绿。若把 competence 的「内容解锁」写成
    「课程解锁」,多邻国(fogg→SDT)与 Keep(cognitive-biases→SDT)双双翻转。

    注:这两次翻转在语义上可能是"变好"——多邻国是 SDT 的教科书案例。但本护栏
    按已批准的验收标准执行:收回线索,不调整期望值。见
    docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md §5。
    """
    expected = {
        "小红书 (RED)": "hook-model",
        "多邻国": "fogg-behavior-model",
        "拼多多": "cialdini-influence",
        "Keep": "cognitive-biases",
        "王者荣耀": "cialdini-influence",
        "金铲铲之战": "variable-ratio-reinforcement",
    }
    library = load_frameworks()
    conn = sqlite3.connect(_CASES_DB)
    rows = list(conn.execute("SELECT product_name, case_json FROM cases"))
    conn.close()
    assert len(rows) == 6, f"预期 6 个案例,实际 {len(rows)}"

    for name, case_json in rows:
        product = json.loads(case_json)["result"]["product"]
        # 与 steps.retrieve 构造关键词的方式保持一致
        keywords = [product["product_type"], *product["touchpoints"]]
        keywords += [f["name"] for f in product["features"]]
        result = retrieve_frameworks(library, keywords=keywords, max_n=8, min_n=0)
        assert result[0].id == expected[name], (
            f"{name} 头名从 {expected[name]} 变为 {result[0].id}"
        )
```

- [ ] **Step 2: 本地运行,确认真的跑了且通过**

```bash
python -m pytest tests/kb/test_retrieval_coverage.py -v
```

Expected: 4 passed(护栏那条**不是** skipped——本机 `.field-test/store/cases.db` 存在)。

若它显示 `SKIPPED`,说明工作目录不是仓库根,`Path` 相对路径没解析到。改用
`python -m pytest` 从仓库根运行,不要为此把 skipif 删掉。

- [ ] **Step 3: 故意验证护栏有效(反向测试)**

临时把 YAML 里 `内容解锁` 改回 `课程解锁`,重跑:

```bash
python -m pytest tests/kb/test_retrieval_coverage.py::test_existing_cases_keep_their_head_framework -v
```

Expected: **FAIL**,消息形如 `多邻国 头名从 fogg-behavior-model 变为 self-determination-theory`。

这一步确认护栏不是永真断言。确认后把 `课程解锁` 改回 `内容解锁`,重跑确认 4 passed。

- [ ] **Step 4: 跑全量并提交**

```bash
python -m pytest -q
```

Expected: `232 passed, 2 skipped`。

```bash
git add tests/kb/test_retrieval_coverage.py
git commit -m "test(kb): 既有 6 案例头名护栏(本地跑,无 db 则跳过)"
```

---

## Task 4: 记录 IDF 稀释度量

**Files:**
- Modify: `docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md`(§5 追加实测)

spec §5 要求「实现时须测量并记录新增线索后全库 df 分布的变化」。度量已做,本任务只是归档。

- [ ] **Step 1: 复现度量**

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
print(f'N={len(pools)} 词元总数={len(df)} df直方图={dict(sorted(hist.items()))}')
print(f'IDF 区间 {math.log(len(pools)/max(df.values())):.3f}~{math.log(len(pools)/1):.3f}')
PY
```

Expected: `N=8 词元总数=416 df直方图={1: 383, 2: 27, 3: 6}`,`IDF 区间 0.981~2.079`。

- [ ] **Step 2: 在 spec §5 末尾追加实测结果**

在 `## 5. 稀释风险与护栏` 的最后一行(「若某条增补线索使既有案例头名翻转…」)之后追加:

```markdown
### 实测结果(实现后回填)

| 指标 | 改前 | 改后 |
|------|------|------|
| 全库词元总数 | 403 | 416 |
| df 直方图 | `{1: 373, 2: 24, 3: 6}` | `{1: 383, 2: 27, 3: 6}` |
| IDF 区间 | 0.981~2.079 | 0.981~2.079 |

**稀释未发生。** df 上限仍为 3,IDF 区间逐位不变;新增的 13 个词元里 10 个是 df=1
的独有词元,只有 3 个把某词元从 df=1 抬到 df=2。原因是补入的表层词汇本就不在其他
框架的线索池中——这也反过来说明"词汇层级错位"确实是 SDT 独有的问题。
```

- [ ] **Step 3: 提交**

```bash
git add docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md
git commit -m "docs: 回填 IDF 稀释实测 — df 上限未变,无稀释"
```

---

## Task 5: 两处 spec 修正

**Files:**
- Modify: `docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md`(§11 第一条)
- Modify: `docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md`(§4 追加)

- [ ] **Step 1: 重写 v7 spec §11 第一条的实测表**

在 `2026-08-03-v7-framework-retrieval-design.md` 中,把 `### 一、无命中时仍退回字母序` 这一节里的实测表及其结论段替换掉。

原文(待替换,从「实测(仅种子库 8 个框架):」到「…理财、工具类产品在当前知识库下仍会落回字母序。」):

```markdown
实测(仅种子库 8 个框架):

| 产品画像 | 非零框架数 | 返回结果 |
|---------|-----------|---------|
| 记账 App | **0 / 8** | `cialdini, cognitive-biases, flow, fogg, hook`(纯字母序,即修复前行为) |
| 冥想 App | 1 / 8 | 1 个命中 + 4 个字母序补齐 |
| 金铲铲 | 8 / 12 | 全部由打分决出 |

**结论要说准确:v7 修好的是"能匹配上时,匹配得对不对";没有修"匹配不上时怎么办"。** 金铲铲之所以效果显著,是因为它的关键词确实与 `variable-ratio-reinforcement` 的线索大量重合。理财、工具类产品在当前知识库下仍会落回字母序。
```

替换为:

```markdown
> ⚠️ **本节原实测数据有误,已于 2026-08-04 更正。** 原表用的画像只有 3 个关键词
> (`记账App / 每日提醒 / 账单分类`),而 step1 产出的真实画像有 12~19 个关键词
> (实测 6 案例:小红书 12、多邻国 12、拼多多 13、Keep 13、王者荣耀 13、金铲铲 19)。
> 稀疏画像放大了零覆盖的程度。详见
> `2026-08-04-nongame-clue-coverage-design.md` 第 1 节。

实测(仅种子库 8 个框架,画像按真实丰度取 12 词):

| 产品画像 | 非零框架数 | 头名 | 语义判定 |
|---------|-----------|------|---------|
| 记账 App | 6 / 8 | `fogg-behavior-model` | ✓ |
| 待办清单 App | 6 / 8 | `flow` | ✓ |
| 冥想睡眠 App | 7 / 8 | `self-determination-theory` | ✓(2026-08-04 补线索后;补前为 ✗) |
| 金铲铲 | 8 / 12 | `variable-ratio-reinforcement` | ✓ |

**结论要说准确:字母序补齐这条限制在机制上依然存在**——补齐循环按 `library` 顺序
遍历,而 `load_frameworks` 按 `id` 排序。但它的实际触发面比原文写的窄得多:按真实
画像丰度,非游戏品类也有 6~7 个非零框架,并不会整体落回字母序。真正暴露出来的问题
不是覆盖率,而是**头名语义是否正确**——冥想 App 曾由 `cognitive-biases` 靠三个零碎
通用词元夺魁。该问题已由补足 SDT 表层线索修掉。
```

同时把该节最后一段的「后续方向」改为:

```markdown
这不比修复前更差,但**不应把 v7 描述为"检索问题已解决"**。字母序补齐仅在关键词与
全部框架零交集时才暴露(实测需画像极稀疏),优先级因此下调。后续方向:让补齐按某种
有意义的次序(如框架通用性)而非 `id` 字典序。知识库线索覆盖已于 2026-08-04 处理。
```

- [ ] **Step 2: 在本次 spec §4 记录「课程解锁」的收回**

在 `2026-08-04-nongame-clue-coverage-design.md` 的 `### 改动:self-determination-theory 的 look_for` 表格之后、「其他框架**仅在验证不达标时才动**」之前,插入:

```markdown
> **实现修正一:`课程解锁` 已收回,改写为 `内容解锁`。** 它引入词元 `课程`,与 DB 中
> 多邻国的触点「课程完成结算页」及 Keep 的功能相撞,使这两个既有案例的头名双双翻到
> `self-determination-theory`,违反第 3 节第 2 条硬性护栏。逐条剔除实验证明它是唯一
> 肇因;改写为不含 `课程` 的同义写法后三个验证画像仍全部达标。按第 5 节的规定处置:
> 收回线索,不调整期望值。
>
> **实现修正二:增补线索从 14 条压到 9 条。** `自选内容`、`逐级进阶`、`关卡`、`组队`、
> `分享给朋友` 被剔除:三个验证画像一条都不命中它们,故无从证明其必要(第 4 节"避免
> 过度添加导致稀释"),而 `组队` 只在王者荣耀触发、`分享给朋友` 只在拼多多与 Keep
> 触发——恰是 SDT **不该**领衔的案例,纯属把噪声推向 SDT。删后全库词元 426→416,
> 三画像与六案例判定一字不变。最终 9 条:autonomy 加 `跳过引导`/`免打扰`/`自定义时长`,
> competence 加 `内容解锁`/`完成率`/`时长统计`,relatedness 加 `好友`/`一起`/`同伴`。
>
> **实现修正三:冥想验证画像重做,原版是同义反复。** 原版用「冥想时长统计」「正念课程
> 逐级解锁」,与线索「时长统计」「内容解锁」几乎逐字相同,SDT 65% 的分来自这两条;
> 同时去掉它们 SDT 即与 `cognitive-biases` 打平并因库序落败。画像与线索属闭环共同设计,
> 测试因此无法独立佐证"SDT 适合冥想类产品"。现版改为自然语序,穷举验证任意去掉 3 个
> 关键词 SDT 仍居首(0/220 失守),最大单词元占比 39%→14%。
>
> **一并记录一个反对意见,留待后续决定:** 那两次翻转在语义上可能是"变好"而非
> "变坏"——多邻国是 SDT 的教科书案例,Keep 由 SDT 领衔也比 `cognitive-biases`
> 更站得住。也就是说,「既有案例头名一个都不改变」这条护栏把**修复前的头名当成了
> 基准真值,而那些头名恰是本次要修的浅层匹配产出的**。本次仍按已批准的标准执行
> (它能防止无约束漂移),但该护栏本身是否合理,值得单独讨论。
```

- [ ] **Step 3: 跑全量确认文档改动没碰到代码**

```bash
python -m pytest -q
```

Expected: `232 passed, 2 skipped`。

- [ ] **Step 4: 提交**

```bash
git add docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md
git commit -m "docs: 更正 v7 spec §11 稀疏画像数据,记录课程解锁的收回与反对意见"
```

---

## Task 6: 收尾核对

**Files:** 无改动,只核验。

- [ ] **Step 1: 逐条核对 spec §3 的四条成功标准**

```bash
python -m pytest tests/kb/ -v
```

对照:
1. 三个验证画像头名语义正确 → `test_ledger_app_heads_fogg` / `test_todo_app_heads_flow` / `test_meditation_app_heads_self_determination` 三条 PASS
2. 现有 6 案例头名一个都不改变 → `test_existing_cases_keep_their_head_framework` PASS(非 SKIPPED)
3. 抽卡回归继续通过 → `test_gacha_keywords_retrieve_variable_ratio_first` PASS
4. IDF 稀释可控 → Task 4 已记录:df 上限未变,IDF 区间逐位不变

- [ ] **Step 2: 确认非目标一条都没越界**

```bash
git diff 7cfc391..HEAD --stat
```

Expected: 恰好 4 个文件——
```
docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md
docs/superpowers/specs/2026-08-04-nongame-clue-coverage-design.md
src/psyteardown/data/frameworks/self-determination-theory.yaml
tests/kb/test_retrieval_coverage.py
```

若 `retriever.py`、`models.py`、`steps.py`、`orchestrator.py` 或其他任何 YAML 出现在
列表里,说明越界了(spec §3 非目标:不改 schema、不改算法、不新增框架、不改补齐行为)。

- [ ] **Step 3: 全量 + 报告**

```bash
python -m pytest -q
```

Expected: `232 passed, 2 skipped`。

报告时须说明:本次**没有**验证真实 LLM 拆解效果(只验证了检索层的头名)。要看端到端
效果需跑一次真实拆解,那是独立的一步,不在本计划内。

---

## Self-Review

**Spec 覆盖核对:**

| spec 章节 | 要求 | 落在哪个 Task |
|-----------|------|--------------|
| §1 更正 | v7 §11 数据按真实丰度重写 | Task 5 Step 1 |
| §3 标准 1 | 三画像头名语义正确,测试锁定 | Task 1 + Task 2 |
| §3 标准 2 | 现有 6 案例头名不变 | Task 3 |
| §3 标准 3 | 抽卡回归通过 | Task 2 Step 3、Task 6 Step 1 |
| §3 标准 4 | IDF 稀释可控 | Task 4 |
| §3 非目标 | 不改 schema/算法/框架数/补齐 | Task 6 Step 2 显式核验 |
| §4 画像 | 三个各 12 词 | Task 1 Step 1 |
| §4 改动 | SDT look_for 补表层词 | Task 2 Step 1(减 `课程解锁`,记录于 Task 5 Step 2) |
| §5 度量 | df 分布变化、头名、抽卡 | Task 4、Task 3、Task 2 Step 3 |
| §6 测试策略 | 新模块、种子库、`min_n=0` | Task 1 Step 1 |
| §7 附带修正 | v7 spec §11 | Task 5 Step 1 |

无遗漏。

**占位符扫描:** 无 TBD/TODO;每个改代码的步骤都给了完整代码;每条命令都给了预期输出。

**类型一致性:** 只用 `retrieve_frameworks(library, keywords=..., max_n=..., min_n=...)`
与 `load_frameworks()` 两个既有签名,全计划一致,未定义新类型或函数。测试里的
`_head` 辅助函数在 Task 1 定义、Task 3 复用 `retrieve_frameworks` 而非 `_head`
(因为它要传自己的 library 变量),不冲突。

**测试计数一致性:** 228(基线)→ 231(Task 2,+3 条画像)→ 232(Task 3,+1 条护栏)。
Task 4/5/6 不加测试。全计划引用的数字与此一致。
