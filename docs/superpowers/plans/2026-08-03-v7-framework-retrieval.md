# v7 框架检索层重写 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重写 step2 框架检索打分,让知识库里语义相关的框架真正能被检索到,解除「实际使用框架数恒为 5 且新增框架零使用」的瓶颈。

**Architecture:** 把打分从「产品关键词 vs 框架 `tags` 的子串匹配」改为「产品关键词 vs (`tags` + 所有原则 `look_for`) 的字符 bigram 重叠,按 IDF 加权」。截断从固定 `top_n=5` 改为「得分 > 0 全入选,夹在 `[min_n=5, max_n=8]`」。纯代码改动,零新增依赖,零新增 LLM 调用。

**Tech Stack:** Python 3.12 / pydantic / pytest。仅用标准库 `math`。

**Spec:** `docs/superpowers/specs/2026-08-03-v7-framework-retrieval-design.md`

---

## File Structure

| 文件 | 职责 | 改动 |
|------|------|------|
| `src/psyteardown/kb/retriever.py` | 框架检索打分与选取(唯一实质改动) | 重写(现 28 行) |
| `src/psyteardown/pipeline/steps.py` | step2 包装,拼关键词后调检索 | 仅参数透传改名 |
| `src/psyteardown/pipeline/orchestrator.py` | 流水线编排 | 仅参数透传改名 |
| `src/psyteardown/growth/proposer.py` | learn 候选框架 prompt | 加一句中文约束 |
| `tests/kb/test_retriever.py` | 检索单元测试 | 扩写 |
| `tests/pipeline/test_steps.py` | step2 测试 | 改调用点 |
| `tests/pipeline/test_orchestrator.py` | 编排测试 | 改调用点 |

设计取舍:`_score` 接收**已算好的 bigram 池**而非 `Framework`,避免在循环里为同一框架反复重算池子。这与 spec 第 3 节的示意签名 `_score(fw, kws, idf)` 略有出入,是实现层的效率细化,不改变行为。

**基线:** 当前全量套件 `196 passed, 2 skipped`。每个任务结束时不得低于此。

---

### Task 1: `_bigrams` 字符二元组切分 ⚠️ 已被 Task 1b 取代

> **本任务已执行完毕(commit c6eef28),但其实现随后被 Task 1b 修正。**
> 若你在读这份计划准备动手,**跳过 Task 1,直接看 Task 1b** —— 那里有最终形态。
> 保留本节仅为记录演进过程。

**Files:**
- Modify: `src/psyteardown/kb/retriever.py`
- Test: `tests/kb/test_retriever.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/kb/test_retriever.py` 末尾(文件顶部已有 `from psyteardown.kb.retriever import retrieve_frameworks`,新增一行导入):

```python
from psyteardown.kb.retriever import _bigrams


def test_bigrams_splits_chinese():
    assert _bigrams("抽卡保底") == {"抽卡", "卡保", "保底"}


def test_bigrams_strips_whitespace():
    assert _bigrams("刷新 动画") == {"刷新", "新动", "动画"}


def test_bigrams_too_short_returns_empty():
    assert _bigrams("卡") == set()
    assert _bigrams("") == set()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/kb/test_retriever.py -k bigrams -v`
Expected: FAIL — `ImportError: cannot import name '_bigrams'`

- [ ] **Step 3: 实现**

在 `src/psyteardown/kb/retriever.py` 顶部,把首行 docstring 与导入改为:

```python
"""框架检索:产品关键词与框架线索的字符 bigram 重叠,按 IDF 加权打分。
接口签名为将来换向量检索预留。"""

import math

from psyteardown.kb.models import Framework


def _bigrams(text: str) -> set[str]:
    """取字符 2-gram;先去掉所有空白。长度 < 2 → 空集。"""
    s = "".join(text.split())
    return {s[i:i + 2] for i in range(len(s) - 1)}
```

保留文件中原有的 `_score` 与 `retrieve_frameworks` 不动(后续任务替换)。

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py -k bigrams -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "feat(kb): _bigrams 字符二元组切分"
```

---

### Task 1b: 拉丁按整词切分 + `_bigrams` 更名 `_tokens`

**Files:**
- Modify: `src/psyteardown/kb/retriever.py`
- Test: `tests/kb/test_retriever.py`

**为何存在这个任务:** Task 1 的代码审查发现,对拉丁文本做字符 bigram 会制造假阳性。实测关键词加入 `Leaderboard` 后,`fogg-behavior-model` 从 0 分跳到 **5.55**、`peak-end-rule` 从 2.08 跳到 7.62,全部来自 `Leaderboard` 与其 tag `onboarding` 共享的 `ar`/`bo`/`oa`/`rd`。**IDF 无法挽救**——这些 bigram 确实罕见,反被赋予高权重。真实语料普遍含拉丁串(`Auto Battler`、`Battle Pass`、`Duolingo`、`ELO`、`iPhone`)。

改后实测:fogg 回到 0.00、peak-end 回到 2.08,`variable-ratio-reinforcement` 仍以 9.70 居首,spec 第 5 节 6 案例回测分数完全不变。

同时把 `_bigrams` 更名为 `_tokens`——拉丁走整词后,「bigrams」这个名字已不准确。

- [ ] **Step 1: 改写测试**

把 Task 1 添加的 3 个 `test_bigrams_*` 测试**整体删除**,替换为以下 8 个(注意导入名也要从 `_bigrams` 改为 `_tokens`):

```python
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
    assert _tokens("刷新 动画") == {"刷新", "动画"}  # 不再跨隙产生「新动」


def test_tokens_two_chars_is_boundary():
    assert _tokens("卡片") == {"卡片"}


def test_tokens_dedups_repeats():
    assert _tokens("卡卡卡") == {"卡卡"}


def test_tokens_too_short_returns_empty():
    assert _tokens("卡") == set()
    assert _tokens("") == set()
    assert _tokens("、,。") == set()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/kb/test_retriever.py -k tokens -v`
Expected: FAIL — `ImportError: cannot import name '_tokens'`

- [ ] **Step 3: 实现**

把 `src/psyteardown/kb/retriever.py` 顶部的导入与 `_bigrams` 整体替换为:

```python
import math
import re

from psyteardown.kb.models import Framework

_LATIN_RUN = re.compile(r"[A-Za-z0-9]+")
_CJK_RUN = re.compile(r"[一-鿿]+")


def _tokens(text: str) -> set[str]:
    """检索用词元:连续中文段切字符 2-gram,连续拉丁/数字段取整词并转小写。

    字符 n-gram 是中文分词的手段;拉丁文本自带词边界,按字符切只会制造假匹配
    (Leaderboard 与 onboarding 共享 ar/bo/oa/rd)。空白与标点一律作分隔符。
    """
    tokens = {word.lower() for word in _LATIN_RUN.findall(text)}
    for run in _CJK_RUN.findall(text):
        tokens |= {run[i:i + 2] for i in range(len(run) - 1)}
    return tokens
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py -k tokens -v`
Expected: 8 passed

Run: `python -m pytest -q`
Expected: `204 passed, 2 skipped`(196 基线 + 8 个新测试;Task 1 的 3 个已被替换)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "fix(kb): 拉丁按整词切分,_bigrams 更名 _tokens

字符 n-gram 对拉丁文本制造假阳性:Leaderboard 与 tag onboarding 共享
ar/bo/oa/rd,使 fogg-behavior-model 从 0 分跳到 5.55。IDF 无法挽救,
因这些 bigram 确实罕见反被赋予高权重。改后噪声归零,回测分数不变。"
```

---

### Task 2: `_pool` 框架词元池(tags + look_for)

**Files:**
- Modify: `src/psyteardown/kb/retriever.py`
- Test: `tests/kb/test_retriever.py`

- [ ] **Step 1: 写失败测试**

```python
from psyteardown.kb.retriever import _pool


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


def test_pool_empty_when_no_tags_no_clues():
    fw = _fw_with_clues("a", [], [])
    assert _pool(fw) == set()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/kb/test_retriever.py -k pool -v`
Expected: FAIL — `ImportError: cannot import name '_pool'`

- [ ] **Step 3: 实现**

在 `_tokens` 之后追加:

```python
def _pool(framework: Framework) -> set[str]:
    """框架的词元池:tags + 所有原则的 look_for。"""
    pool: set[str] = set()
    for tag in framework.tags:
        pool |= _tokens(tag)
    for principle in framework.principles:
        for clue in principle.look_for:
            pool |= _tokens(clue)
    return pool
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py -k pool -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "feat(kb): _pool 合并 tags 与 look_for 的 bigram 池"
```

---

### Task 3: `_idf` 逆文档频率权重

**Files:**
- Modify: `src/psyteardown/kb/retriever.py`
- Test: `tests/kb/test_retriever.py`

- [ ] **Step 1: 写失败测试**

```python
from psyteardown.kb.retriever import _idf


def test_idf_common_bigram_weighs_zero():
    # "进度" 出现在全部 2 个池中 → log(2/2) = 0
    idf = _idf([{"进度", "抽卡"}, {"进度", "签到"}])
    assert idf["进度"] == 0.0


def test_idf_unique_bigram_weighs_most():
    idf = _idf([{"进度", "抽卡"}, {"进度", "签到"}])
    assert idf["抽卡"] > idf["进度"]
    assert idf["抽卡"] == idf["签到"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/kb/test_retriever.py -k idf -v`
Expected: FAIL — `ImportError: cannot import name '_idf'`

- [ ] **Step 3: 实现**

在 `_pool` 之后追加:

```python
def _idf(pools: list[set[str]]) -> dict[str, float]:
    """log(N / df):出现在全部框架中的 bigram 权重为 0,越独特权重越高。"""
    n = len(pools)
    df: dict[str, int] = {}
    for pool in pools:
        for bigram in pool:
            df[bigram] = df.get(bigram, 0) + 1
    return {bigram: math.log(n / count) for bigram, count in df.items()}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py -k idf -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "feat(kb): _idf 逆文档频率,压低通用 bigram 权重"
```

---

### Task 4: `_score` IDF 加权重叠打分

**Files:**
- Modify: `src/psyteardown/kb/retriever.py`(替换旧 `_score`)
- Test: `tests/kb/test_retriever.py`

- [ ] **Step 1: 写失败测试**

```python
from psyteardown.kb.retriever import _score


def test_score_sums_idf_of_overlapping_bigrams():
    idf = {"抽卡": 2.0, "保底": 1.0}
    # 关键词 "抽卡保底" 的 bigram 为 {抽卡, 卡保, 保底};池中命中 抽卡 与 保底
    assert _score({"抽卡", "保底"}, ["抽卡保底"], idf) == 3.0


def test_score_zero_when_no_overlap():
    assert _score({"抽卡"}, ["每日签到"], {"抽卡": 2.0}) == 0.0


def test_score_ignores_bigram_missing_from_idf():
    assert _score({"抽卡"}, ["抽卡"], {}) == 0.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/kb/test_retriever.py -k score -v`
Expected: FAIL — 旧 `_score(framework, keywords)` 签名不符,报 `TypeError` 或断言失败

- [ ] **Step 3: 实现**

删除文件中原有的 `_score` 函数(整个 `def _score(framework, keywords)` 块),在 `_idf` 之后追加:

```python
def _score(pool: set[str], keywords: list[str], idf: dict[str, float]) -> float:
    """命中词元的 IDF 权重之和。pool 由调用方预先算好,避免重复计算。"""
    total = 0.0
    for keyword in keywords:
        for token in _tokens(keyword) & pool:
            total += idf.get(token, 0.0)
    return total
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py -k score -v`
Expected: 3 passed

（此时 `retrieve_frameworks` 仍调用旧签名,套件会红。Task 5 修复。）

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "feat(kb): _score 改为 IDF 加权 bigram 重叠"
```

---

### Task 5: `retrieve_frameworks` 新选取规则

**Files:**
- Modify: `src/psyteardown/kb/retriever.py`
- Test: `tests/kb/test_retriever.py`(改写 4 个既有测试 + 新增边界测试)

- [ ] **Step 1: 写失败测试**

把 `tests/kb/test_retriever.py` 中 4 个既有测试的 `top_n=` 全部改为 `max_n=`,并把 `test_no_match_falls_back_to_top_n` 改名:

```python
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
```

再追加边界测试:

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/kb/test_retriever.py -v`
Expected: FAIL — `retrieve_frameworks() got an unexpected keyword argument 'max_n'`

- [ ] **Step 3: 实现**

用以下内容替换文件中原有的 `retrieve_frameworks`:

```python
def retrieve_frameworks(
    library: list[Framework],
    keywords: list[str],
    *,
    max_n: int = 8,
    min_n: int = 5,
) -> list[Framework]:
    """得分 > 0 的按分降序返回,数量夹在 [floor, max_n];同分保持库序。
    floor = min(min_n, max_n, len(library));非零不足 floor 时按库序补齐,
    保证流水线不空转。"""
    if not library or max_n <= 0:
        return []

    pools = [_pool(fw) for fw in library]
    idf = _idf(pools)
    scored = [(fw, _score(pool, keywords, idf)) for fw, pool in zip(library, pools)]
    # sorted 稳定:同分保持原库顺序
    ranked = [fw for fw, s in sorted(scored, key=lambda x: -x[1]) if s > 0]

    if len(ranked) >= max_n:
        return ranked[:max_n]

    floor = min(min_n, max_n, len(library))
    chosen = list(ranked)
    picked = {fw.id for fw in chosen}
    for fw in library:
        if len(chosen) >= floor:
            break
        if fw.id not in picked:
            chosen.append(fw)
    return chosen
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py -v`
Expected: 全部 passed(4 个改写 + 5 个新增 + 前三任务的 10 个）

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "feat(kb): 检索改为得分>0全入选,夹在 [min_n, max_n]"
```

---

### Task 6: 参数改名透传到 steps 与 orchestrator

**Files:**
- Modify: `src/psyteardown/pipeline/steps.py:27-33`
- Modify: `src/psyteardown/pipeline/orchestrator.py:23`, `:30`
- Test: `tests/pipeline/test_steps.py:35`, `tests/pipeline/test_orchestrator.py:41`

- [ ] **Step 1: 改测试调用点(先让测试表达新契约)**

`tests/pipeline/test_steps.py` 第 35 行:

```python
    frameworks = steps.retrieve(_profile(), library, max_n=1)
```

`tests/pipeline/test_orchestrator.py` 第 41 行:

```python
        generated_at="2026-06-13", max_n=5,
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/pipeline/ -v`
Expected: FAIL — `retrieve() got an unexpected keyword argument 'max_n'`

- [ ] **Step 3: 实现**

`src/psyteardown/pipeline/steps.py` 的 `retrieve` 整体替换为:

```python
def retrieve(
    profile: ProductProfile,
    library: list[Framework],
    max_n: int = 8,
    min_n: int = 5,
) -> list[Framework]:
    """Step 2:纯代码,按产品类型/功能/触点关键词检索相关框架。"""
    keywords = [profile.product_type, *profile.touchpoints]
    keywords += [f.name for f in profile.features]
    return retrieve_frameworks(library, keywords=keywords, max_n=max_n, min_n=min_n)
```

`src/psyteardown/pipeline/orchestrator.py`:把第 23 行的 `top_n: int = 5,` 替换为两行:

```python
    max_n: int = 8,
    min_n: int = 5,
```

把第 30 行替换为:

```python
    frameworks = steps.retrieve(profile, library, max_n=max_n, min_n=min_n)
```

- [ ] **Step 4: 运行全量测试**

Run: `python -m pytest -q`
Expected: `196 passed, 2 skipped` 之上(新增测试计入),无 failed

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/steps.py src/psyteardown/pipeline/orchestrator.py tests/pipeline/
git commit -m "refactor(pipeline): top_n 更名 max_n 并透传 min_n"
```

---

### Task 7: 回归测试锁死本次 bug

**Files:**
- Test: `tests/kb/test_retriever.py`

本测试只用**随包分发的种子库**(不含 gitignore 的 learned 目录),因此确定性可重现。已实测:种子库 8 个框架下,该组关键词使 `variable-ratio-reinforcement` 得 9.7 分排第一,`fogg-behavior-model` 得 0 分不入选,非零仅 3 个故会补齐到 floor=5。

- [ ] **Step 1: 写测试**

```python
from psyteardown.kb.loader import load_frameworks


def test_gacha_keywords_retrieve_variable_ratio_first():
    """回归:抽卡/自走棋关键词必须检索到可变比率强化。

    历史 bug:打分只看 tags 且用子串匹配,导致该框架永远进不了 top-5,
    step3 从未见过它,自评却反复指出它缺席。
    """
    library = load_frameworks()  # 仅种子,不依赖 gitignore 的 learned 目录
    keywords = [
        "自走棋/Auto Battler手游",
        "商店刷新动画",
        "概率抽取与共享卡池",
        "小小英雄开蛋",
        "海克斯强化三选一",
    ]
    result = retrieve_frameworks(library, keywords=keywords, max_n=8)
    ids = [fw.id for fw in result]
    assert ids[0] == "variable-ratio-reinforcement"
    # 通用 bigram(进度/操作/时间)造成的假阳性不得挤到它前面
    assert "fogg-behavior-model" not in ids[: ids.index("variable-ratio-reinforcement")]
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/kb/test_retriever.py::test_gacha_keywords_retrieve_variable_ratio_first -v`
Expected: PASS(实现已在 Task 5 完成,本测试是行为锁)

若 FAIL,说明 Task 5 的实现与设计不符,回查 `_score`/`_idf`,不要修改断言。

- [ ] **Step 3: 提交**

```bash
git add tests/kb/test_retriever.py
git commit -m "test(kb): 回归锁定抽卡关键词必须检索到可变比率强化"
```

---

### Task 8: 修 learn 候选框架的 tag 语言约束

**Files:**
- Modify: `src/psyteardown/growth/proposer.py:47`

背景:该 prompt 对 `tags` 语言无任何约束,已产出英文 tag 的框架(`cyclical-ownership-reset` 的 tags 为 `ownership`/`scarcity` 等),与中文产品关键词结构性不匹配。改后不影响已入库框架(它们的 `look_for` 本就是中文,现已参与打分)。

- [ ] **Step 1: 实现**

`src/psyteardown/growth/proposer.py` 中把这一行:

```python
        "category、summary、tags、principles(每条含 id/name/description/look_for)、"
```

替换为:

```python
        "category、summary、tags、principles(每条含 id/name/description/look_for)、"
        "其中 tags 与 look_for 必须使用中文(id 保持 kebab-case 英文),"
        "因为检索按中文产品描述与它们做匹配;"
```

- [ ] **Step 2: 运行全量测试**

Run: `python -m pytest -q`
Expected: 无 failed(该 prompt 由 FakeProvider 消费,测试不断言其文本)

- [ ] **Step 3: 提交**

```bash
git add src/psyteardown/growth/proposer.py
git commit -m "fix(growth): learn 候选框架要求中文 tags/look_for"
```

---

### Task 9: 行为验收(真实 LLM,非单元测试)

**Files:**
- Create: `.field-test/reports/jinchanchan-v5.md`

spec 第 9 节的验收方式。用**未改动的**输入重跑,与 v4 对照。

- [ ] **Step 1: 移除旧案例避免自我锚定**

检索会以极高相似度召回同产品旧案例,把上一版结论重新喂给模型,须先删:

```bash
python -c "
import sqlite3
c=sqlite3.connect('.field-test/store/cases.db')
c.execute(\"delete from cases where product_name like '%金铲铲%'\")
c.commit()
print('剩余:', [r[0] for r in c.execute('select product_name from cases')])
"
```

Expected: 剩余 5 个案例,无金铲铲

- [ ] **Step 2: 重跑拆解**

```bash
source .env.local && psyteardown analyze \
  -i .field-test/products/jinchanchan.txt --format md \
  --store .field-test/store/cases.db \
  --use-memory --use-strategies --self-review \
  --out .field-test/reports/jinchanchan-v5.md
```

Expected: 输出「已写入 ...jinchanchan-v5.md」与「已落盘案例 <id>」。耗时约 10-20 分钟,建议后台跑。

- [ ] **Step 3: 核对三条验收标准**

```bash
echo "1. 可变比率强化是否被使用:"; grep -c "variable-ratio-reinforcement" .field-test/reports/jinchanchan-v5.md
echo "2. 实际使用框架数(需 > 5):"; grep -oE '`[a-z-]+·' .field-test/reports/jinchanchan-v5.md | sort -u | wc -l
echo "3. 自评是否仍称其漏拆:"; grep -c "variable ratio\|可变比率" <(sed -n '/## 拆解自评/,/## 附录/p' .field-test/reports/jinchanchan-v5.md)
```

Expected:
1. > 0(v4 为 0)
2. > 5(v1~v4 恒为 5)
3. 自评的**缺陷**段落不再把它列为漏拆(第 3 条需人工读一眼确认语义,计数只作提示)

**不得用自评分变化作为验收依据** —— v1~v3 三版内容差异显著却都是 0.62,该指标已证明不具区分度。

- [ ] **Step 4: 用真实实现复核 6 案例回测**

spec 第 5 节的回测是设计阶段用原型脚本算的。这一步确认**落地实现**与原型一致——头名框架应为:拼多多→`near-goal-persistence`、多邻国→`cumulative-progress-retrieval`、王者荣耀→`cyclical-ownership-reset`、小红书→`hook-model`、Keep→`dynamic-social-competition`、金铲铲→`variable-ratio-reinforcement`。

```bash
source .env.local && python -c "
import sqlite3, json
from pathlib import Path
from psyteardown.kb.loader import load_frameworks
from psyteardown.kb.retriever import retrieve_frameworks
lib = load_frameworks(learned_dir=Path('.field-test/store/learned'))
c = sqlite3.connect('.field-test/store/cases.db')
for name, cj in c.execute('select product_name, case_json from cases'):
    p = json.loads(cj)['result']['product']
    kws = [p['product_type'], *p['touchpoints']] + [f['name'] for f in p['features']]
    top = retrieve_frameworks(lib, keywords=kws, max_n=8)[0].id
    print(f'{name:<14} → {top}')
"
```

Expected: 6 行输出,头名与上表一致(金铲铲一行需先跑完 Step 2 才有案例)

若某案例头名与设计阶段不符,不要改期望值——先确认是否因案例库内容变动(learned 框架增减会改变 IDF 分母)导致,并把差异记入 field-test。

- [ ] **Step 5: 提交**

```bash
git add .field-test/reports/jinchanchan-v5.md
git commit -m "field-test: v7 检索改造后重跑,验证框架覆盖度"
```

---

## 完成后

全量套件应为 `196 + 新增测试数` passed,`2 skipped`,无 failed。

若 Task 9 的第 2 条(使用框架数 > 5)未达成,不要改断言或回退代码——先用下面的诊断脚本看检索实际返回了什么,再判断是检索层还是 step3 的问题:

```bash
source .env.local && python -c "
import sqlite3, json
from pathlib import Path
from psyteardown.kb.loader import load_frameworks
from psyteardown.kb.retriever import retrieve_frameworks
c=sqlite3.connect('.field-test/store/cases.db')
prof=json.loads(c.execute(\"select case_json from cases where product_name like '%金铲铲%'\").fetchone()[0])['result']['product']
kws=[prof['product_type'], *prof['touchpoints']]+[f['name'] for f in prof['features']]
lib=load_frameworks(learned_dir=Path('.field-test/store/learned'))
print('检索返回:', [f.id for f in retrieve_frameworks(lib, keywords=kws, max_n=8)])
"
```

检索返回了但报告里没用到 → 问题在 step3;检索就没返回 → 问题在打分。
