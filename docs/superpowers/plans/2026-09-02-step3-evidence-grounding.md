# step3 证据溯源 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Mapping.evidence` 收紧为产品原文的逐字片段,纯代码归一化校验,未通过即丢弃并记入 `GroundingStats`;同时消除 `feature` 字段的幽灵功能名。

**Architecture:** 新增纯函数模块 `pipeline/grounding.py`(归一化 + 子串判定);`map_features` 接收产品原文、prompt 注入逐字引用规则、返回 `(mappings, stats)`;orchestrator 透传 `description` 并把 stats 挂进 `TeardownResult.grounding`;报告渲染「原文依据」+ 丢弃计数 + 丢弃附录。Spec:`docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md`。

**Tech Stack:** Python 3.12 / pydantic / pytest。全部离线测试,真实 LLM 实验只在最后一个任务。

**Baseline(本计划起点,main `3c2b6a6`):** `249 passed, 2 skipped`。分支:`v9/evidence-grounding`。

---

## 计划外改动 = 越界

`retriever.py`、KB YAML、step4/step5 的 prompt、`cli.py`、`mcp_server/` 一律不动。
spec §2 非目标写得明确:step4/5 溯源与 LLM 裁判都是后续阶段。

## File Structure

| 文件 | 责任 | 动作 |
|------|------|------|
| `src/psyteardown/pipeline/grounding.py` | 归一化 + 逐字子串判定,纯函数 | 新建 |
| `src/psyteardown/pipeline/schemas.py` | `GroundingStats`;`TeardownResult.grounding` | 修改 |
| `src/psyteardown/pipeline/steps.py` | `map_features`:收原文、注入规则、校验、覆写 feature、返回 tuple | 修改 |
| `src/psyteardown/pipeline/orchestrator.py` | 透传 description,挂 grounding | 修改 |
| `src/psyteardown/report/render.py` | 「原文依据」、丢弃计数行、丢弃附录 | 修改 |
| `tests/pipeline/test_grounding.py` | grounding 纯函数测试 | 新建 |
| `tests/pipeline/test_schemas.py` | GroundingStats 默认值 + 旧 JSON 兼容 | 修改 |
| `tests/pipeline/test_steps.py` | step3 新行为 4 条 + 既有 2 条更新 | 修改 |
| `tests/pipeline/test_steps_memory.py` | 签名更新(加 description 实参) | 修改 |
| `tests/pipeline/test_steps_strategy.py` | 签名更新(仅 1 处直接调用) | 修改 |
| `tests/pipeline/test_orchestrator.py` | grounding 断言 + 丢弃记录测试 | 修改 |
| `tests/report/test_render.py` | 渲染 3 条新测试 | 修改 |
| `docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md` | §8 实验结果回填 | 修改(Task 7) |

测试计数:起点 249 → Task 1 加 9 → Task 2 加 2 → Task 3 加 4 → Task 4 加 1 →
Task 5 加 3 → **268 passed, 2 skipped**。实现时以实际输出为准,不符先查原因再继续。

---

### Task 1: grounding 纯函数模块

**Files:**
- Create: `tests/pipeline/test_grounding.py`
- Create: `src/psyteardown/pipeline/grounding.py`

- [ ] **Step 0: 建分支**

```bash
git checkout -b v9/evidence-grounding
```

- [ ] **Step 1: 写失败测试**

新建 `tests/pipeline/test_grounding.py`,完整内容:

```python
"""grounding 纯函数:归一化 + 逐字子串判定。全部离线。

SOURCE 仿照 chaoxi.txt 的真实风格。关键背景(spec §5.1):step1 会把输入的半角
, ( ) 归一成全角 , ( ),不做归一化时真实引用的逐字命中率只有 1/9。
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
    # 引用带全角逗号「,」,原文是半角「,」:归一化后仍应命中
    # (step1 实测就是这么改写标点的,spec §5.1:不归一化命中率只有 1/9)
    assert is_grounded("可单独播放或叠加混音,支持定时关闭", SOURCE)


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
```

- [ ] **Step 2: 跑,确认按预期失败**

```bash
python -m pytest tests/pipeline/test_grounding.py -v
```

Expected: 全部 ERROR,`ModuleNotFoundError: No module named 'psyteardown.pipeline.grounding'`。

- [ ] **Step 3: 实现**

新建 `src/psyteardown/pipeline/grounding.py`,完整内容:

```python
"""证据溯源:校验 evidence 是否为产品原文的逐字片段。

纯函数,不认识 LLM。归一化规则与实测依据见
docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md §5。
"""

import unicodedata

# 短于此的引用(归一化后计)判为未溯源:「专注」这类两字词天然是子串,
# 能通过校验却什么都证明不了。6 = 「支持定时关闭」这类最短有效引用的长度。
MIN_QUOTE_CHARS = 6


def normalize(text: str) -> str:
    """NFKC(全角→半角)→ casefold → 只留字母数字(一举去掉空白与全部标点,
    含 NFKC 不覆盖的 。、「」《》·—)。"""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in folded if ch.isalnum())


def is_grounded(quote: str, source: str) -> bool:
    """quote 归一化后长度达标、且是 source 归一化后的子串,才算可溯源。"""
    q = normalize(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in normalize(source)
```

- [ ] **Step 4: 跑,确认通过**

```bash
python -m pytest tests/pipeline/test_grounding.py -v
```

Expected: **9 passed**。全量 `python -m pytest -q` → `258 passed, 2 skipped`。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/grounding.py tests/pipeline/test_grounding.py
git commit -m "feat(pipeline): grounding 纯函数 — 归一化 + 逐字子串判定"
```

---

### Task 2: GroundingStats 与 TeardownResult.grounding

**Files:**
- Modify: `src/psyteardown/pipeline/schemas.py`
- Modify: `tests/pipeline/test_schemas.py`

- [ ] **Step 1: 写失败测试**

在 `tests/pipeline/test_schemas.py` 末尾追加(并在文件头的 import 里加入
`GroundingStats`,同时在文件顶部加 `import json`):

```python
def test_grounding_stats_defaults():
    stats = GroundingStats()
    assert (stats.kept, stats.dropped, stats.dropped_mappings) == (0, 0, [])


def test_teardown_result_without_grounding_key_still_validates():
    """存量案例 JSON(v8 及以前)没有 grounding 字段,必须照常反序列化。"""
    result = TeardownResult(
        product=ProductProfile(name="D", product_type="t", one_liner="o",
                               features=[], touchpoints=[]),
        frameworks_used=[], mappings=[],
        assessment=ExperienceAssessment(),
        executive_summary="s",
        meta=TeardownMeta(model="fake", generated_at="t"),
    )
    payload = json.loads(result.model_dump_json())
    del payload["grounding"]
    old = TeardownResult.model_validate(payload)
    assert old.grounding.kept == 0 and old.grounding.dropped == 0
```

- [ ] **Step 2: 跑,确认失败**

```bash
python -m pytest tests/pipeline/test_schemas.py -v
```

Expected: 新 2 条 FAIL(`ImportError: cannot import name 'GroundingStats'`)。

- [ ] **Step 3: 实现**

`src/psyteardown/pipeline/schemas.py`,在 `MappingList` 类之后插入:

```python
class GroundingStats(BaseModel):
    """step3 证据溯源记账。只统计参与校验的条目(m.error 为空者):
    kept + dropped = LLM 成功返回的映射总数,不含调用失败的占位条目。
    保留被丢弃条目全文,供事后归类「真编造」还是「改写误伤」(spec §8 标准 3)。"""

    kept: int = 0
    dropped: int = 0
    dropped_mappings: list[Mapping] = Field(default_factory=list)
```

`TeardownResult` 中,在 `assessment` 字段之前加一行:

```python
    grounding: GroundingStats = Field(default_factory=GroundingStats)
```

- [ ] **Step 4: 跑,确认通过**

```bash
python -m pytest tests/pipeline/test_schemas.py -v && python -m pytest -q
```

Expected: `test_schemas.py` **6 passed**;全量 `260 passed, 2 skipped`。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/schemas.py tests/pipeline/test_schemas.py
git commit -m "feat(pipeline): GroundingStats 记账模型,旧案例 JSON 带默认值兼容"
```

---

### Task 3: map_features — 收原文、校验、覆写 feature、返回 tuple

**Files:**
- Modify: `src/psyteardown/pipeline/steps.py:49-92`
- Modify: `tests/pipeline/test_steps.py`
- Modify: `tests/pipeline/test_steps_memory.py:30-42`(仅加实参)
- Modify: `tests/pipeline/test_steps_strategy.py:29-35`(仅加实参)

注意:本 Task 结束时 `orchestrator.py` 还没改,凡经 `run_teardown` 的测试都是红的
(含 `test_steps_strategy.py` 里 2 条)。**因此 Task 3 不提交、不跑全量**,只跑
定向测试确认本层正确;Task 4 改完 orchestrator、全量回绿后,两个 Task 一次提交。
不留红提交。

- [ ] **Step 1: 更新 + 新增测试**

`tests/pipeline/test_steps.py` 整体改动。文件头 import 增加 `GroundingStats`(实际
未直接用到类型可不加;下方代码未引用,故 import 不变)。在 `_profile()` 之后加:

```python
_DESC = "Demo App:每日签到拿奖励,完成后收到推送提醒。"
```

把 `test_step3_maps_each_feature` 与 `test_step3_failure_marks_error_and_continues`
替换为,并追加 4 条新测试:

```python
def test_step3_maps_each_feature():
    mapping = Mapping(
        feature="签到", framework_id="habit", principle_id="p",
        rationale="r", evidence="每日签到拿奖励", confidence=0.9,
    )
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[mapping]),
        MappingList(mappings=[]),  # 触点「推送」无映射
    ])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert mappings[0].feature == "签到"
    assert stats.kept == 1 and stats.dropped == 0


def test_step3_failure_marks_error_and_continues():
    # 队列耗尽 → 每个目标映射失败,应返回带 error 的占位 mapping 而非崩溃
    provider = FakeProvider(structured_responses=[])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert len(mappings) == 2  # 1 feature + 1 touchpoint
    assert all(m.error is not None for m in mappings)
    # 失败占位条目不参与溯源记账(spec §6)
    assert stats.kept == 0 and stats.dropped == 0


def test_step3_prompt_contains_source_and_quote_rules():
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[]), MappingList(mappings=[]),
    ])
    steps.map_features(provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    prompt = provider.calls[0]["prompt"]
    assert _DESC in prompt          # 产品原文全文必须进 step3(v8 及以前从未进过)
    assert "逐字复制" in prompt
    assert "宁可少给" in prompt


def test_step3_drops_ungrounded_evidence():
    good = Mapping(feature="签到", framework_id="habit", principle_id="p",
                   rationale="r", evidence="每日签到拿奖励", confidence=0.9)
    bad = Mapping(feature="签到", framework_id="habit", principle_id="p",
                  rationale="r", evidence="连续打卡显示徽章与排行榜", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[good, bad]), MappingList(mappings=[]),
    ])
    mappings, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert [m.evidence for m in mappings] == ["每日签到拿奖励"]
    assert stats.kept == 1 and stats.dropped == 1
    assert stats.dropped_mappings[0].evidence == "连续打卡显示徽章与排行榜"


def test_step3_overwrites_feature_with_target():
    # 实验实测:模型把 feature 写成「睡眠模块 - 连续睡眠打卡」这类 step1 从未
    # 产出的幽灵功能名。名字以调用目标为准,细分意图请模型写进 rationale。
    ghost = Mapping(feature="签到 - 连续签到打卡", framework_id="habit",
                    principle_id="p", rationale="r",
                    evidence="每日签到拿奖励", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[ghost]), MappingList(mappings=[]),
    ])
    mappings, _ = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert mappings[0].feature == "签到"


def test_step3_dropped_mapping_also_gets_target_feature():
    # 丢弃条目进附录,幽灵功能名同样要覆写,否则附录里全是模型自拼的名字
    bad = Mapping(feature="幽灵功能", framework_id="habit", principle_id="p",
                  rationale="r", evidence="原文里不存在的编造内容", confidence=0.9)
    provider = FakeProvider(structured_responses=[
        MappingList(mappings=[bad]), MappingList(mappings=[]),
    ])
    _, stats = steps.map_features(
        provider, _profile(), [_fw("habit", ["习惯养成"])], _DESC)
    assert stats.dropped_mappings[0].feature == "签到"
```

(新增净 4 条:原 2 条更新 + `prompt_contains`/`drops_ungrounded`/`overwrites_feature`/
`dropped_also_gets_target`;`error_not_counted` 的断言并入
`test_step3_failure_marks_error_and_continues`,不单开。)

`tests/pipeline/test_steps_memory.py` 两处调用加第 4 个位置实参:

```python
# 第 32 行
    steps.map_features(provider, _profile(), [_fw()], "每日签到App描述",
                       prior_summary="- 旧产品X(一句话):用过框架 hook-model")
# 第 41 行
    steps.map_features(provider, _profile(), [_fw()], "每日签到App描述")  # 默认 None
```

`tests/pipeline/test_steps_strategy.py` 第 31 行同理:

```python
    steps.map_features(provider, _profile(), [_fw()], "产品描述文本",
                       strategy_guidance="- 社交产品优先社交证明")
```

- [ ] **Step 2: 跑,确认新测试失败**

```bash
python -m pytest tests/pipeline/test_steps.py -v
```

Expected: step3 相关全 FAIL(`map_features() missing 1 required positional argument:
'description'` 或解包错误)。step1/2/4/5 测试 PASS。

- [ ] **Step 3: 实现**

`src/psyteardown/pipeline/steps.py`:import 区加一行:

```python
from psyteardown.pipeline.grounding import is_grounded
```

同文件把 `GroundingStats` 加进 `from psyteardown.pipeline.schemas import (...)` 列表。
`map_features` 整体替换为:

```python
def map_features(
    provider: LLMProvider,
    profile: ProductProfile,
    frameworks: list[Framework],
    description: str,
    prior_summary: str | None = None,
    strategy_guidance: str | None = None,
) -> tuple[list[Mapping], GroundingStats]:
    """Step 3:逐功能/触点映射到框架原则。单项失败标 error 并继续。

    description=产品原文,evidence 的唯一合法来源:prompt 要求逐字引用,
    is_grounded 校验,未通过的映射丢弃并记入 GroundingStats(spec 2026-09-02)。
    prior_summary=历史相似案例;strategy_guidance=历史归纳的拆解策略(均仅供参考)。"""
    brief = _frameworks_brief(frameworks)
    valid_ids = ", ".join(fw.id for fw in frameworks)
    ref_block = ""
    if prior_summary:
        ref_block = (
            "\n以下是仅供参考的历史相似案例,请独立判断当前产品,不要照搬:\n"
            f"{prior_summary}\n"
        )
    if strategy_guidance:
        ref_block += (
            "\n以下是历史归纳的拆解策略,供参考,请结合当前产品独立判断:\n"
            f"{strategy_guidance}\n"
        )
    targets = [f.name for f in profile.features] + profile.touchpoints
    mappings: list[Mapping] = []
    stats = GroundingStats()
    for target in targets:
        prompt = (
            f"产品原文(evidence 的唯一合法来源):\n{description}\n\n"
            f"可用心理学框架:\n{brief}\n"
            f"{ref_block}\n"
            f"产品「{profile.name}」的功能/触点:「{target}」。\n"
            "请判断它用到了哪个框架的哪条原则、为何有效,并给出 0-1 的置信度。"
            f"framework_id 必须来自这些 id: {valid_ids}。"
            "若适用多条,返回最贴切的若干条 mapping。\n"
            "字段硬性要求:\n"
            "- evidence 必须是上方产品原文中的一段连续原文,逐字复制,不得改写、拼接、增删;\n"
            "- 原文中找不到支持该判断的文字,就不要产出这条 mapping;宁可少给,不可编造;\n"
            "- 一切解读、推理、心理学解释写进 rationale,不得写进 evidence。"
        )
        try:
            result = provider.structured_complete(prompt, MappingList, system=_SYSTEM)
        except LLMError as e:
            mappings.append(
                Mapping(
                    feature=target, framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error=str(e),
                )
            )
            continue
        for m in result.mappings:
            m.feature = target  # 幽灵功能名以调用目标为准;细分意图在 rationale
            if is_grounded(m.evidence, description):
                mappings.append(m)
                stats.kept += 1
            else:
                stats.dropped += 1
                stats.dropped_mappings.append(m)
    return mappings, stats
```

- [ ] **Step 4: 定向跑(不跑全量,原因见本 Task 开头)**

```bash
python -m pytest tests/pipeline/test_steps.py tests/pipeline/test_steps_memory.py -v
python -m pytest tests/pipeline/test_steps_strategy.py -k "map_features or assess" -v
```

Expected: 第一条 **12 passed**(test_steps 10 + memory 2);第二条 **2 passed**。
`test_steps_strategy.py` 里 2 条走 `run_teardown` 的测试此刻红,Task 4 修复。

- [ ] **Step 5: 暂存,不提交**

```bash
git add src/psyteardown/pipeline/steps.py tests/pipeline/test_steps.py tests/pipeline/test_steps_memory.py tests/pipeline/test_steps_strategy.py
```

提交在 Task 4 Step 5 与 orchestrator 改动合并进行,保证不留红提交。

---

### Task 4: orchestrator 透传与挂载

**Files:**
- Modify: `src/psyteardown/pipeline/orchestrator.py:34-36,41-55`
- Modify: `tests/pipeline/test_orchestrator.py`

- [ ] **Step 1: 更新 + 新增测试**

`tests/pipeline/test_orchestrator.py` 的 `test_run_teardown_full_pipeline` 中,
`mapping` 的 `evidence="e"` 改为 `evidence="每日签到App描述"`(与传入
`run_teardown` 的 description 逐字一致),并在断言块末尾追加:

```python
    assert result.grounding.kept == 1
    assert result.grounding.dropped == 0
```

文件末尾追加新测试:

```python
def test_run_teardown_records_dropped_mappings():
    """未溯源映射不进 result.mappings,但全文进 grounding.dropped_mappings。"""
    profile = ProductProfile(
        name="Demo", product_type="App", one_liner="每日签到App",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=["推送"],
    )
    fabricated = Mapping(
        feature="签到", framework_id="habit", principle_id="trigger",
        rationale="r", evidence="连续打卡显示徽章与排行榜", confidence=0.9,
    )
    provider = FakeProvider(structured_responses=[
        profile,
        MappingList(mappings=[fabricated]),
        MappingList(mappings=[]),
        ExperienceAssessment(),
        Synthesis(executive_summary="总结"),
    ])
    result = run_teardown(
        provider, "每日签到App描述", library=_library(),
        generated_at="t", max_n=5,
    )
    assert result.mappings == []
    assert result.grounding.dropped == 1
    assert result.grounding.dropped_mappings[0].evidence == "连续打卡显示徽章与排行榜"
```

- [ ] **Step 2: 跑,确认失败**

```bash
python -m pytest tests/pipeline/test_orchestrator.py -v
```

Expected: `test_run_teardown_full_pipeline` 与新测试 FAIL(tuple 解包
`ValidationError` 或 `TypeError`)。

- [ ] **Step 3: 实现**

`src/psyteardown/pipeline/orchestrator.py` 第 34-36 行改为:

```python
    mappings, grounding_stats = steps.map_features(
        provider, profile, frameworks, description,
        prior_summary=prior_summary,
        strategy_guidance=map_guide or None)
```

`TeardownResult(...)` 构造中,`mappings=mappings,` 之后加一行:

```python
        grounding=grounding_stats,
```

- [ ] **Step 4: 全量,确认回绿**

```bash
python -m pytest -q
```

Expected: `265 passed, 2 skipped`(260 + steps 4 + orchestrator 1)。

- [ ] **Step 5: 提交(含 Task 3 暂存的改动,一次绿提交)**

```bash
git add src/psyteardown/pipeline/orchestrator.py tests/pipeline/test_orchestrator.py
git commit -m "feat(pipeline): step3 收产品原文逐字校验 evidence,未溯源丢弃记账"
```

此提交包含 Task 3 已暂存的 `steps.py` 及三个测试文件。

---

### Task 5: 报告渲染

**Files:**
- Modify: `src/psyteardown/report/render.py:44-52,74-76`
- Modify: `tests/report/test_render.py`

- [ ] **Step 1: 写失败测试**

`tests/report/test_render.py` 文件头 import 区把 `GroundingStats` 加进
`from psyteardown.pipeline.schemas import (...)`,文件末尾追加:

```python
def test_markdown_uses_source_evidence_label():
    md = render_markdown(_result())
    assert "原文依据:" in md
    assert "体现:" not in md


def test_markdown_dropped_count_and_appendix():
    result = _result()
    result.grounding = GroundingStats(
        kept=2, dropped=1,
        dropped_mappings=[Mapping(
            feature="签到", framework_id="hook-model", principle_id="trigger",
            rationale="r", evidence="连续打卡显示徽章", confidence=0.8)],
    )
    md = render_markdown(result)
    assert "丢弃 1 条未溯源映射(参与校验共 3 条)" in md
    assert "## 附录:未溯源而丢弃的映射" in md
    assert "连续打卡显示徽章" in md


def test_markdown_no_dropped_section_when_zero():
    # grounding 全零(含旧案例默认值)时,报告与从前一样只字不提溯源
    md = render_markdown(_result())
    assert "未溯源" not in md
```

- [ ] **Step 2: 跑,确认失败**

```bash
python -m pytest tests/report/test_render.py -v
```

Expected: 新 3 条 FAIL(「原文依据」缺失等),旧 10 条 PASS。

- [ ] **Step 3: 实现**

`src/psyteardown/report/render.py` 三处。

第一处,`render_markdown` 第 3 节循环里 `f"  - 体现:{m.evidence}\n"` 改为:

```python
            f"  - 原文依据:{m.evidence}\n"
```

第二处,该循环结束后、`out.append("")` 之前插入:

```python
    g = result.grounding
    if g.dropped > 0:
        out.append(
            f"\n本次丢弃 {g.dropped} 条未溯源映射"
            f"(参与校验共 {g.kept + g.dropped} 条),详见附录。"
        )
```

第三处,在「# 7. 附录:引用框架 + 出处」注释块之前插入:

```python
    # 6.6 附录:未溯源而丢弃的映射(evidence 在原文中找不到,按设计不进正文)
    if result.grounding.dropped > 0:
        out.append("## 附录:未溯源而丢弃的映射\n")
        for m in result.grounding.dropped_mappings:
            out.append(
                f"- **{m.feature}** → `{m.framework_id}·{m.principle_id}`:{m.evidence}"
            )
        out.append("")
```

- [ ] **Step 4: 跑,确认通过**

```bash
python -m pytest tests/report/test_render.py -v && python -m pytest -q
```

Expected: `test_render.py` **13 passed**;全量 `268 passed, 2 skipped`。

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/report/render.py tests/report/test_render.py
git commit -m "feat(report): 原文依据标签 + 未溯源丢弃计数与附录"
```

---

### Task 6: 越界核对与合并前收尾

- [ ] **Step 1: 核对非目标未越界**

```bash
git diff main..HEAD --stat -- src/
```

Expected: 只有 `grounding.py`(新)、`schemas.py`、`steps.py`、`orchestrator.py`、
`render.py`。`retriever.py`、`cli.py`、`mcp_server/`、KB YAML 出现即为越界,回查原因。

- [ ] **Step 2: 全量最终确认**

```bash
python -m pytest -q
```

Expected: `268 passed, 2 skipped`。

- [ ] **Step 3: 报告**

向用户说明:离线部分完成;**尚未**跑真实 LLM 实验,spec §8 三条验收标准全部待验,
Task 7 需要 DeepSeek API key 且产生一次真实调用花费。

---

### Task 7: 真实实验与 spec §8 回填(需真实 LLM,单独执行)

**Files:**
- Create: `.field-test/reports/chaoxi-grounded.md`
- Create: `.field-test/experiments/chaoxi-grounded.json`
- Modify: `docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md`

前置:`DEEPSEEK_API_KEY`(在 `.env.local`);对照基线
`.field-test/experiments/chaoxi-maxn12.json`(42 条映射,9 条越界,21.4%)。
案例 id 由描述哈希生成,同输入复跑会覆盖库中旧案例——基线已备份在
`experiments/`,可直接跑。

- [ ] **Step 1: 跑实验(输入逐字不变,唯一变量是本次改动)**

```bash
psyteardown analyze -i .field-test/products/chaoxi.txt \
  --store .field-test/store/cases.db --self-review --max-n 12 \
  --provider deepseek --format md --out .field-test/reports/chaoxi-grounded.md
```

- [ ] **Step 2: 导出案例 JSON 存档**

```bash
python - <<'PY'
import json, sqlite3
conn = sqlite3.connect(".field-test/store/cases.db")
row = conn.execute(
    "SELECT case_json FROM cases WHERE case_id='803b9a231399f660'").fetchone()
open(".field-test/experiments/chaoxi-grounded.json", "w", encoding="utf-8").write(row[0])
print("saved", len(row[0]), "bytes")
PY
```

- [ ] **Step 3: 按 spec §8 判定(尺子已锁定,不得调整)**

1. **标准 1(越界率 ≤ 5%):** 逐条读保留映射的 evidence 与 rationale,对照
   `chaoxi.txt` 第 14~21 行 7 条事实边界,计越界条数。与基线 9/42 同一把尺。
2. **标准 2(保留 ≥ 25 条):** `grounding.kept`。
3. **标准 3(丢弃中真编造 ≥ 50%):** 逐条读 `grounding.dropped_mappings`,按 spec
   §8 定义归类「真编造」/「改写误伤」。

**标准 3 不通过时不得宣称成功**——那说明逐字要求在误伤,方向转 spec §10
(覆盖率匹配),而不是收工。

- [ ] **Step 4: 回填 spec 与提交**

在 spec 末尾按 no-truncate 实验 §7 的格式追加「实验结果(2026-XX-XX 回填)」一节:
命令、三条标准逐条结果与判定表、明确不作为依据的观察(自评总分等)。

```bash
git add .field-test/reports/chaoxi-grounded.md .field-test/experiments/chaoxi-grounded.json docs/superpowers/specs/2026-09-02-step3-evidence-grounding-design.md
git commit -m "docs: step3 证据溯源实验结果 — 三条标准逐条回填"
```

---

## Self-Review

**Spec 覆盖:**

| spec 章节 | 落点 |
|-----------|------|
| §3 evidence 语义收紧 | Task 3(prompt 三条硬性要求) |
| §4 grounding.py 纯函数 + 数据流三处透传 | Task 1 + Task 3 + Task 4 |
| §4 返回值改 tuple | Task 3 Step 3,调用方仅 orchestrator(Task 4) |
| §5.1 归一化实测依据 | Task 1 测试注释引用;测试用例覆盖全角标点与前缀改写两个实测模式 |
| §5.2 三步归一化 + MIN_QUOTE_CHARS=6 | Task 1(常量由测试锁定) |
| §5.3 error 条目不参与校验 | Task 3(`test_step3_failure...` 断言 stats 全零) |
| §6 GroundingStats 计数语义 + 旧 JSON 兼容 | Task 2 |
| §6 渲染三处 | Task 5 |
| §7 feature 覆写(含丢弃条目) | Task 3 两条测试 |
| §8 三条验收标准 | Task 7(尺子原文引用,不复述阈值以外的自由发挥) |
| §2 非目标 | 「计划外改动 = 越界」节 + Task 6 Step 1 显式核验 |

**占位符扫描:** 无 TBD;每个改代码步骤均含完整代码与预期输出。Task 7 的人工归类
本质是人做的判定,已给出所依据的行号与定义出处,不属于占位。

**类型一致性:** `map_features` 返回 `tuple[list[Mapping], GroundingStats]`,Task 3
定义、Task 4 解包;`GroundingStats` 字段名 kept/dropped/dropped_mappings 在 Task 2/3/5
三处一致;`is_grounded(quote, source)` 参数序在 Task 1 定义与 Task 3 调用一致。

**测试计数核算:** 249 → +9(grounding)= 258 → +2(schemas)= 260 → +4(steps 净增:
test_steps.py 由 6 条变 10 条)= 264 → +1(orchestrator)= 265 → +3(render)= 268。
中间态:Task 3 不提交(经 `run_teardown` 的测试红着),Task 4 Step 4 全量回绿后
一次提交,历史上不存在红提交。
