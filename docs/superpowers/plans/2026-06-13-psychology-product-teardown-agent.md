# 心理驱动型产品拆解 Agent v1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个 Python 库 `psyteardown` + 薄 CLI:给定产品文字描述,基于精选心理学框架知识库,经多步流水线产出结构化拆解报告(Markdown / JSON)。

**Architecture:** 干净的库内核分四个子系统——知识库(`kb`)、拆解流水线(`pipeline`,方案 B 的 5 步)、可插拔 LLM provider(`llm`,默认 Claude)、报告渲染(`report`)。CLI 仅为薄入口。流水线各步依赖注入的 `LLMProvider` 接口,测试时注入 `FakeProvider`,核心逻辑无需真实 API。

**Tech Stack:** Python 3.11+、Pydantic v2(数据模型 + LLM 结构化输出 + 序列化)、PyYAML(知识库)、anthropic SDK(默认 provider)、Typer(CLI)、pytest(测试)。LLM 默认模型 `claude-opus-4-8`,结构化输出用 `client.messages.parse(output_format=...)`。

> **实现说明:** spec 中数据模型画作 dataclass;本计划统一改用 Pydantic `BaseModel`,以同时满足 `messages.parse` 的结构化输出、校验与 JSON 序列化。这是落地选型,不改变设计意图。

---

## 文件结构

```
pyproject.toml                         # 项目元数据 + 依赖 + 入口脚本
src/psyteardown/
├── __init__.py
├── kb/
│   ├── __init__.py
│   ├── models.py                       # Framework / Principle (Pydantic)
│   ├── loader.py                       # 加载 + 校验 data/frameworks/*.yaml
│   └── retriever.py                    # 标签/关键词检索(纯代码)
├── pipeline/
│   ├── __init__.py
│   ├── schemas.py                      # 各步输入/输出 Pydantic 模型 + TeardownResult
│   ├── steps.py                        # 5 步函数,各接收注入的 provider
│   └── orchestrator.py                 # 串联 5 步 → TeardownResult
├── llm/
│   ├── __init__.py
│   ├── base.py                         # LLMProvider 抽象 + FakeProvider
│   └── claude.py                       # ClaudeProvider(默认实现)
├── report/
│   ├── __init__.py
│   └── render.py                       # TeardownResult → Markdown / JSON
└── cli.py                              # Typer 薄 CLI
src/psyteardown/data/frameworks/        # 种子知识库(随包分发)
│   ├── fogg-behavior-model.yaml
│   ├── hook-model.yaml
│   ├── cialdini-influence.yaml
│   ├── self-determination-theory.yaml
│   ├── peak-end-rule.yaml
│   ├── cognitive-biases.yaml
│   └── flow.yaml
tests/
├── conftest.py
├── kb/
│   ├── test_models.py
│   ├── test_loader.py
│   ├── test_retriever.py
│   └── test_seed_frameworks.py
├── llm/
│   └── test_fake_provider.py
├── pipeline/
│   ├── test_steps.py
│   └── test_orchestrator.py
└── report/
    └── test_render.py
```

---

## Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `src/psyteardown/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 写 `pyproject.toml`**

```toml
[project]
name = "psyteardown"
version = "0.1.0"
description = "心理驱动型产品拆解 Agent(v1):基于心理学框架拆解产品体验"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "typer>=0.12",
    "anthropic>=0.69",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
psyteardown = "psyteardown.cli:app"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
psyteardown = ["data/frameworks/*.yaml"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: 创建空包文件**

`src/psyteardown/__init__.py`:
```python
"""psyteardown — 心理驱动型产品拆解 Agent(v1)。"""

__version__ = "0.1.0"
```

`tests/conftest.py`:
```python
"""共享测试夹具。"""
```

- [ ] **Step 3: 安装并验证环境**

Run: `pip install -e ".[dev]" && python -c "import psyteardown; print(psyteardown.__version__)"`
Expected: 输出 `0.1.0`,无报错

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml src/psyteardown/__init__.py tests/conftest.py
git commit -m "chore: scaffold psyteardown package"
```

---

## Task 2: 知识库数据模型

**Files:**
- Create: `src/psyteardown/kb/__init__.py`
- Create: `src/psyteardown/kb/models.py`
- Test: `tests/kb/test_models.py`

- [ ] **Step 1: 写失败测试**

`tests/kb/__init__.py`: 空文件。
`tests/kb/test_models.py`:
```python
from psyteardown.kb.models import Framework, Principle


def test_framework_parses_from_dict():
    fw = Framework.model_validate(
        {
            "id": "fogg-behavior-model",
            "name": "Fogg 行为模型",
            "category": "motivation",
            "summary": "行为 = 动机 × 能力 × 提示。",
            "tags": ["行为触发", "习惯养成"],
            "principles": [
                {
                    "id": "trigger",
                    "name": "提示",
                    "description": "需要提示来触发行为。",
                    "look_for": ["推送", "红点"],
                }
            ],
            "references": ["Fogg, B.J. (2009)."],
            "ethics_notes": "可被用于暗黑模式。",
        }
    )
    assert fw.id == "fogg-behavior-model"
    assert fw.principles[0].look_for == ["推送", "红点"]
    assert fw.ethics_notes == "可被用于暗黑模式。"


def test_ethics_notes_optional():
    fw = Framework.model_validate(
        {
            "id": "x",
            "name": "X",
            "category": "cognition",
            "summary": "s",
            "tags": [],
            "principles": [],
            "references": [],
        }
    )
    assert fw.ethics_notes is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/kb/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.kb'`

- [ ] **Step 3: 实现模型**

`src/psyteardown/kb/__init__.py`: 空文件。
`src/psyteardown/kb/models.py`:
```python
"""知识库数据模型:心理学框架及其原则。"""

from pydantic import BaseModel, Field


class Principle(BaseModel):
    id: str
    name: str
    description: str
    look_for: list[str] = Field(default_factory=list)  # 拆解时的观察线索


class Framework(BaseModel):
    id: str
    name: str
    category: str  # motivation / persuasion / cognition / emotion / habit ...
    summary: str
    tags: list[str] = Field(default_factory=list)
    principles: list[Principle] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    ethics_notes: str | None = None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/kb/test_models.py -v`
Expected: PASS(2 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/__init__.py src/psyteardown/kb/models.py tests/kb/__init__.py tests/kb/test_models.py
git commit -m "feat: add knowledge base data models"
```

---

## Task 3: 知识库加载器

**Files:**
- Create: `src/psyteardown/kb/loader.py`
- Test: `tests/kb/test_loader.py`

- [ ] **Step 1: 写失败测试**

`tests/kb/test_loader.py`:
```python
import pytest

from psyteardown.kb.loader import load_frameworks, KBLoadError


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


VALID_YAML = """
id: test-fw
name: 测试框架
category: motivation
summary: 一句话摘要。
tags: [转化]
principles:
  - id: p1
    name: 原则一
    description: 描述。
    look_for: [按钮]
references: ["Ref 2020."]
ethics_notes: 注意事项。
"""


def test_load_valid_directory(tmp_path):
    _write(tmp_path, "test-fw.yaml", VALID_YAML)
    frameworks = load_frameworks(tmp_path)
    assert len(frameworks) == 1
    assert frameworks[0].id == "test-fw"


def test_load_sorts_by_id(tmp_path):
    _write(tmp_path, "b.yaml", VALID_YAML.replace("test-fw", "bbb"))
    _write(tmp_path, "a.yaml", VALID_YAML.replace("test-fw", "aaa"))
    frameworks = load_frameworks(tmp_path)
    assert [f.id for f in frameworks] == ["aaa", "bbb"]


def test_bad_yaml_raises_kbloaderror(tmp_path):
    _write(tmp_path, "broken.yaml", "id: x\nname: [unclosed")
    with pytest.raises(KBLoadError) as exc:
        load_frameworks(tmp_path)
    assert "broken.yaml" in str(exc.value)


def test_missing_required_field_raises_kbloaderror(tmp_path):
    _write(tmp_path, "bad.yaml", "id: x\n")  # 缺 name/category/summary
    with pytest.raises(KBLoadError) as exc:
        load_frameworks(tmp_path)
    assert "bad.yaml" in str(exc.value)


def test_missing_directory_raises_kbloaderror(tmp_path):
    with pytest.raises(KBLoadError):
        load_frameworks(tmp_path / "does-not-exist")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/kb/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.kb.loader'`

- [ ] **Step 3: 实现加载器**

`src/psyteardown/kb/loader.py`:
```python
"""从 YAML 文件加载并校验心理学框架知识库。"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from psyteardown.kb.models import Framework

# 随包分发的种子知识库目录
DEFAULT_KB_DIR = Path(__file__).parent.parent / "data" / "frameworks"


class KBLoadError(Exception):
    """加载或校验知识库失败。"""


def load_frameworks(directory: Path | None = None) -> list[Framework]:
    """加载目录下所有 *.yaml 框架,按 id 升序返回。坏文件/坏 schema 抛 KBLoadError。"""
    directory = directory or DEFAULT_KB_DIR
    if not directory.is_dir():
        raise KBLoadError(f"知识库目录不存在: {directory}")

    frameworks: list[Framework] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise KBLoadError(f"YAML 解析失败 {path.name}: {e}") from e
        try:
            frameworks.append(Framework.model_validate(raw))
        except ValidationError as e:
            raise KBLoadError(f"框架校验失败 {path.name}: {e}") from e

    frameworks.sort(key=lambda f: f.id)
    return frameworks
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/kb/test_loader.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/loader.py tests/kb/test_loader.py
git commit -m "feat: add knowledge base loader with validation"
```

---

## Task 4: 种子知识库(7 个框架)

**Files:**
- Create: `src/psyteardown/data/frameworks/fogg-behavior-model.yaml`
- Create: `src/psyteardown/data/frameworks/hook-model.yaml`
- Create: `src/psyteardown/data/frameworks/cialdini-influence.yaml`
- Create: `src/psyteardown/data/frameworks/self-determination-theory.yaml`
- Create: `src/psyteardown/data/frameworks/peak-end-rule.yaml`
- Create: `src/psyteardown/data/frameworks/cognitive-biases.yaml`
- Create: `src/psyteardown/data/frameworks/flow.yaml`
- Test: `tests/kb/test_seed_frameworks.py`

- [ ] **Step 1: 写失败测试**

`tests/kb/test_seed_frameworks.py`:
```python
from psyteardown.kb.loader import load_frameworks

EXPECTED_IDS = {
    "fogg-behavior-model",
    "hook-model",
    "cialdini-influence",
    "self-determination-theory",
    "peak-end-rule",
    "cognitive-biases",
    "flow",
}


def test_seed_library_loads():
    frameworks = load_frameworks()  # 默认种子目录
    ids = {f.id for f in frameworks}
    assert EXPECTED_IDS <= ids


def test_every_framework_has_principles_and_references():
    for f in load_frameworks():
        assert f.principles, f"{f.id} 缺 principles"
        assert f.references, f"{f.id} 缺 references"
        assert f.tags, f"{f.id} 缺 tags"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/kb/test_seed_frameworks.py -v`
Expected: FAIL — `KBLoadError: 知识库目录不存在` 或断言失败(目录为空)

- [ ] **Step 3: 写 7 个框架 YAML**

`src/psyteardown/data/frameworks/fogg-behavior-model.yaml`:
```yaml
id: fogg-behavior-model
name: Fogg 行为模型
category: motivation
summary: 行为 = 动机 × 能力 × 提示,三者同时满足才发生。
tags: [行为触发, 习惯养成, 转化, onboarding, 推送]
principles:
  - id: motivation
    name: 动机(Motivation)
    description: 用户完成行为的意愿强度,受快感、希望、归属驱动。
    look_for: [奖励, 进度激励, 社交认可, 损失规避文案]
  - id: ability
    name: 能力(Ability)
    description: 降低完成行为所需的努力与成本。
    look_for: [一键操作, 默认值, 减少步骤, 自动填充]
  - id: trigger
    name: 提示(Trigger)
    description: 在动机与能力都足够时,需要提示来触发行为。
    look_for: [推送通知, 红点, 空状态引导, 按钮显著性]
references:
  - "Fogg, B.J. (2009). A behavior model for persuasive design."
ethics_notes: 可被用于暗黑模式(如制造虚假紧迫或滥用推送),拆解时需标注。
```

`src/psyteardown/data/frameworks/hook-model.yaml`:
```yaml
id: hook-model
name: 上瘾模型(Hook)
category: habit
summary: 触发 → 行动 → 多变奖励 → 投入,四步循环形成习惯。
tags: [习惯养成, 留存, 通知, 社交, 内容流]
principles:
  - id: trigger
    name: 触发(Trigger)
    description: 外部触发(通知)与内部触发(情绪)驱动用户回到产品。
    look_for: [推送, 邮件召回, 无聊/孤独时的入口]
  - id: action
    name: 行动(Action)
    description: 用户为获取奖励所做的最简单行为。
    look_for: [下拉刷新, 滑动, 一键点赞]
  - id: variable_reward
    name: 多变奖励(Variable Reward)
    description: 不可预测的奖励最能维持参与。
    look_for: [信息流, 抽奖/盲盒, 点赞数波动]
  - id: investment
    name: 投入(Investment)
    description: 用户投入越多(内容、关系、数据),越难离开。
    look_for: [发帖, 关注关系, 个性化设置, 积累数据]
references:
  - "Eyal, N. (2014). Hooked: How to Build Habit-Forming Products."
ethics_notes: 多变奖励与投入机制易滑向成瘾设计,需评估对用户福祉的影响。
```

`src/psyteardown/data/frameworks/cialdini-influence.yaml`:
```yaml
id: cialdini-influence
name: Cialdini 说服六原则
category: persuasion
summary: 互惠、承诺一致、社会认同、权威、喜好、稀缺六条说服杠杆。
tags: [转化, 付费, 文案, 社交证明, 促销]
principles:
  - id: reciprocity
    name: 互惠
    description: 先给予,用户更倾向回报。
    look_for: [免费试用, 赠品, 先给价值再要求]
  - id: commitment
    name: 承诺与一致
    description: 小承诺引导大承诺,保持自我一致。
    look_for: [分步注册, 先点小目标, 进度条承诺]
  - id: social_proof
    name: 社会认同
    description: 人们参照他人行为决定自身行为。
    look_for: [用户数, 评价, "X 人正在看", 热门榜]
  - id: authority
    name: 权威
    description: 权威背书提升信任。
    look_for: [专家认证, 媒体标识, 奖项徽章]
  - id: liking
    name: 喜好
    description: 越喜欢越容易被说服。
    look_for: [拟人化, 相似性文案, 亲和视觉]
  - id: scarcity
    name: 稀缺
    description: 稀缺与紧迫提升即时行动意愿。
    look_for: [限时, 限量, 倒计时, "仅剩 N 件"]
references:
  - "Cialdini, R. (2006). Influence: The Psychology of Persuasion."
ethics_notes: 稀缺/社会认同极易被伪造(假倒计时、刷量),构成暗黑模式,需重点标注。
```

`src/psyteardown/data/frameworks/self-determination-theory.yaml`:
```yaml
id: self-determination-theory
name: 自我决定论(SDT)
category: motivation
summary: 内在动机由自主、胜任、归属三种基本心理需求驱动。
tags: [内在动机, 留存, 学习, 游戏化, 社区]
principles:
  - id: autonomy
    name: 自主(Autonomy)
    description: 用户感到行为出于自己的选择。
    look_for: [可自定义, 可跳过, 非强制路径]
  - id: competence
    name: 胜任(Competence)
    description: 用户感到自己在进步、能掌控。
    look_for: [难度梯度, 即时反馈, 技能提升曲线]
  - id: relatedness
    name: 归属(Relatedness)
    description: 用户感到与他人连接。
    look_for: [社区, 协作, 互助, 关系绑定]
references:
  - "Deci, E. & Ryan, R. (1985). Self-Determination Theory."
ethics_notes: 健康的内在动机设计;若用外部奖励挤出内在动机则适得其反,可对照评估。
```

`src/psyteardown/data/frameworks/peak-end-rule.yaml`:
```yaml
id: peak-end-rule
name: 峰终定律
category: emotion
summary: 人对体验的记忆主要由情绪峰值与结尾决定,而非整体平均。
tags: [情绪曲线, 体验设计, onboarding, 结算, 流失]
principles:
  - id: peak
    name: 峰值(Peak)
    description: 设计强烈的正向情绪高点。
    look_for: [惊喜时刻, 成就动画, 里程碑庆祝]
  - id: end
    name: 结尾(End)
    description: 体验结尾的情绪强烈影响整体记忆。
    look_for: [完成页, 离开挽留, 结算反馈, 退订体验]
references:
  - "Kahneman, D. (2011). Thinking, Fast and Slow."
ethics_notes: 一般为正向设计;但用结尾情绪操纵(如退订设障)可构成暗黑模式。
```

`src/psyteardown/data/frameworks/cognitive-biases.yaml`:
```yaml
id: cognitive-biases
name: 认知偏误精选
category: cognition
summary: 锚定、默认效应、损失规避、从众等系统性判断偏差被产品广泛利用。
tags: [定价, 决策, 默认项, 文案, 转化]
principles:
  - id: anchoring
    name: 锚定效应
    description: 首个数字成为后续判断的参照锚。
    look_for: [划线原价, 推荐套餐高价在先]
  - id: default_effect
    name: 默认效应
    description: 用户倾向于保持默认选项。
    look_for: [默认勾选, 默认套餐, 默认订阅]
  - id: loss_aversion
    name: 损失规避
    description: 损失带来的痛苦约为同等收益快感的两倍。
    look_for: ["将失去", 连续打卡中断警告, 限免到期]
  - id: bandwagon
    name: 从众效应
    description: 倾向跟随多数人的选择。
    look_for: ["最受欢迎"标签, 热度排序]
references:
  - "Tversky, A. & Kahneman, D. (1974). Judgment under Uncertainty."
ethics_notes: 默认效应与损失规避是暗黑模式高发区(默认订阅、强制流失挽留),需逐项标注。
```

`src/psyteardown/data/frameworks/flow.yaml`:
```yaml
id: flow
name: 心流(Flow)
category: emotion
summary: 当挑战与技能匹配、目标清晰、反馈即时时,用户进入高度专注的沉浸状态。
tags: [沉浸, 游戏化, 学习, 创作工具, 专注]
principles:
  - id: challenge_skill_balance
    name: 挑战-技能平衡
    description: 难度略高于当前技能时最易进入心流。
    look_for: [动态难度, 分级关卡, 个性化推荐难度]
  - id: clear_goals
    name: 清晰目标
    description: 每一步该做什么明确无歧义。
    look_for: [任务清单, 单一主行动, 进度指示]
  - id: immediate_feedback
    name: 即时反馈
    description: 行为后立刻获得结果反馈。
    look_for: [实时校验, 动效反馈, 即时得分]
references:
  - "Csikszentmihalyi, M. (1990). Flow: The Psychology of Optimal Experience."
ethics_notes: 心流可被用于延长停留时长(无尽关卡),需评估是否损害用户时间自主。
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/kb/test_seed_frameworks.py -v`
Expected: PASS(2 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/data/frameworks/ tests/kb/test_seed_frameworks.py
git commit -m "feat: add seed knowledge base (7 frameworks)"
```

---

## Task 5: 框架检索器

**Files:**
- Create: `src/psyteardown/kb/retriever.py`
- Test: `tests/kb/test_retriever.py`

- [ ] **Step 1: 写失败测试**

`tests/kb/test_retriever.py`:
```python
from psyteardown.kb.models import Framework, Principle
from psyteardown.kb.retriever import retrieve_frameworks


def _fw(id_, tags):
    return Framework(
        id=id_, name=id_, category="motivation", summary="s",
        tags=tags, principles=[Principle(id="p", name="p", description="d")],
        references=["r"],
    )


def test_keyword_match_ranks_higher():
    library = [
        _fw("habit", ["习惯养成", "留存"]),
        _fw("pricing", ["定价", "促销"]),
    ]
    result = retrieve_frameworks(library, keywords=["习惯养成"], top_n=2)
    assert result[0].id == "habit"


def test_no_match_falls_back_to_top_n():
    library = [_fw("a", ["x"]), _fw("b", ["y"]), _fw("c", ["z"])]
    result = retrieve_frameworks(library, keywords=["无关词"], top_n=2)
    assert len(result) == 2  # 无匹配也返回 top_n,保证流水线不空转


def test_respects_top_n_limit():
    library = [_fw(str(i), ["习惯养成"]) for i in range(10)]
    result = retrieve_frameworks(library, keywords=["习惯养成"], top_n=3)
    assert len(result) == 3


def test_partial_substring_match_counts():
    library = [_fw("a", ["习惯养成与留存"]), _fw("b", ["定价"])]
    result = retrieve_frameworks(library, keywords=["习惯"], top_n=1)
    assert result[0].id == "a"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/kb/test_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.kb.retriever'`

- [ ] **Step 3: 实现检索器**

`src/psyteardown/kb/retriever.py`:
```python
"""框架检索:v1 用标签/关键词子串匹配打分。接口签名为将来换向量检索预留。"""

from psyteardown.kb.models import Framework


def _score(framework: Framework, keywords: list[str]) -> int:
    """每个关键词若是某 tag 的子串(或反之)记 1 分。"""
    score = 0
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        for tag in framework.tags:
            if kw in tag or tag in kw:
                score += 1
                break
    return score


def retrieve_frameworks(
    library: list[Framework],
    keywords: list[str],
    top_n: int = 5,
) -> list[Framework]:
    """按关键词与 tags 的匹配度返回 Top-N 框架;无匹配则返回前 top_n(稳定不空转)。"""
    ranked = sorted(
        library,
        key=lambda f: (_score(f, keywords), -ord(f.id[0]) if f.id else 0),
        reverse=True,
    )
    return ranked[:top_n]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/kb/test_retriever.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/kb/retriever.py tests/kb/test_retriever.py
git commit -m "feat: add framework retriever (tag/keyword matching)"
```

---

## Task 6: LLM provider 抽象 + FakeProvider

**Files:**
- Create: `src/psyteardown/llm/__init__.py`
- Create: `src/psyteardown/llm/base.py`
- Test: `tests/llm/test_fake_provider.py`

- [ ] **Step 1: 写失败测试**

`tests/llm/__init__.py`: 空文件。
`tests/llm/test_fake_provider.py`:
```python
import pytest
from pydantic import BaseModel

from psyteardown.llm.base import FakeProvider, LLMError


class Demo(BaseModel):
    value: str


def test_structured_complete_returns_queued_instance():
    provider = FakeProvider(structured_responses=[Demo(value="hi")])
    out = provider.structured_complete("prompt", Demo)
    assert isinstance(out, Demo)
    assert out.value == "hi"


def test_structured_complete_validates_dict_against_schema():
    provider = FakeProvider(structured_responses=[{"value": "ok"}])
    out = provider.structured_complete("prompt", Demo)
    assert out.value == "ok"


def test_complete_returns_queued_text():
    provider = FakeProvider(text_responses=["hello"])
    assert provider.complete("prompt") == "hello"


def test_exhausted_queue_raises():
    provider = FakeProvider(structured_responses=[])
    with pytest.raises(LLMError):
        provider.structured_complete("prompt", Demo)


def test_records_calls():
    provider = FakeProvider(text_responses=["a"])
    provider.complete("my-prompt", system="sys")
    assert provider.calls[0]["prompt"] == "my-prompt"
    assert provider.calls[0]["system"] == "sys"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/llm/test_fake_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.llm'`

- [ ] **Step 3: 实现抽象 + FakeProvider**

`src/psyteardown/llm/__init__.py`: 空文件。
`src/psyteardown/llm/base.py`:
```python
"""LLM provider 抽象。pipeline 各步只依赖此接口,不 import 具体 SDK。"""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """LLM 调用或结构化解析失败。"""


class LLMProvider(ABC):
    @abstractmethod
    def structured_complete(
        self, prompt: str, schema: type[T], *, system: str | None = None
    ) -> T:
        """返回校验过的 schema 实例;解析失败由实现内部重试,仍失败抛 LLMError。"""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """返回纯文本回复。"""


class FakeProvider(LLMProvider):
    """测试用:按队列返回预置结果,并记录调用,绝不触网。"""

    def __init__(
        self,
        structured_responses: list | None = None,
        text_responses: list[str] | None = None,
    ):
        self._structured = list(structured_responses or [])
        self._text = list(text_responses or [])
        self.calls: list[dict] = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system, "schema": schema})
        if not self._structured:
            raise LLMError("FakeProvider: structured_responses 队列已耗尽")
        item = self._structured.pop(0)
        if isinstance(item, schema):
            return item
        return schema.model_validate(item)

    def complete(self, prompt, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        if not self._text:
            raise LLMError("FakeProvider: text_responses 队列已耗尽")
        return self._text.pop(0)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/llm/test_fake_provider.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/llm/__init__.py src/psyteardown/llm/base.py tests/llm/__init__.py tests/llm/test_fake_provider.py
git commit -m "feat: add LLMProvider abstraction and FakeProvider"
```

---

## Task 7: ClaudeProvider(默认实现)

**Files:**
- Create: `src/psyteardown/llm/claude.py`

> 说明:本任务**不写单测**(避免触网与依赖真实 key)。正确性由 Task 13 的可选端到端冒烟测试覆盖。代码使用 `anthropic` SDK 的 `messages.parse()`(结构化输出)与 `messages.create()`(纯文本)。模型默认 `claude-opus-4-8`(skill 指定的默认);结构化解析失败时内部重试。

- [ ] **Step 1: 实现 ClaudeProvider**

`src/psyteardown/llm/claude.py`:
```python
"""默认 LLM provider:Anthropic Claude。结构化输出走 messages.parse。"""

import os

import anthropic

from psyteardown.llm.base import LLMError, LLMProvider, T

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 16000


class ClaudeProvider(LLMProvider):
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_retries: int = 2,
        api_key: str | None = None,
    ):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError(
                "未找到 ANTHROPIC_API_KEY。请设置环境变量,或传入 api_key。"
            )
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens
        self._max_retries = max_retries

    def structured_complete(self, prompt, schema: type[T], *, system=None) -> T:
        last_err: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                resp = self._client.messages.parse(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system or anthropic.NOT_GIVEN,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=schema,
                )
                parsed = resp.parsed_output
                if parsed is None:
                    raise LLMError("Claude 返回的结构化输出无法解析为目标 schema")
                return parsed
            except (anthropic.APIError, LLMError) as e:
                last_err = e
        raise LLMError(f"结构化调用在重试后仍失败: {last_err}") from last_err

    def complete(self, prompt, *, system=None) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as e:
            raise LLMError(f"文本调用失败: {e}") from e
        return "".join(b.text for b in resp.content if b.type == "text")
```

- [ ] **Step 2: 验证可导入(不调用 API)**

Run: `python -c "from psyteardown.llm.claude import ClaudeProvider, DEFAULT_MODEL; print(DEFAULT_MODEL)"`
Expected: 输出 `claude-opus-4-8`,无导入错误

- [ ] **Step 3: 提交**

```bash
git add src/psyteardown/llm/claude.py
git commit -m "feat: add ClaudeProvider (default LLM implementation)"
```

---

## Task 8: 流水线 schemas

**Files:**
- Create: `src/psyteardown/pipeline/__init__.py`
- Create: `src/psyteardown/pipeline/schemas.py`
- Test: `tests/pipeline/test_schemas.py`

> 说明:Step3 的逐功能映射用一个 `MappingList` 包装器(`messages.parse` 需要顶层为 object,不能直接是 array)。

- [ ] **Step 1: 写失败测试**

`tests/pipeline/__init__.py`: 空文件。
`tests/pipeline/test_schemas.py`:
```python
from psyteardown.pipeline.schemas import (
    Feature,
    ProductProfile,
    Mapping,
    MappingList,
    ExperienceAssessment,
    TeardownResult,
    TeardownMeta,
)


def test_product_profile_roundtrip():
    p = ProductProfile(
        name="Demo", product_type="App", one_liner="一句话",
        features=[Feature(name="f", description="d", user_goal="g")],
        touchpoints=["onboarding"],
    )
    assert p.features[0].name == "f"


def test_mapping_defaults_error_none():
    m = Mapping(
        feature="f", framework_id="fogg-behavior-model", principle_id="trigger",
        rationale="r", evidence="e", confidence=0.8,
    )
    assert m.error is None


def test_teardown_result_serializes_to_json():
    result = TeardownResult(
        product=ProductProfile(
            name="Demo", product_type="App", one_liner="x",
            features=[], touchpoints=[],
        ),
        frameworks_used=["fogg-behavior-model"],
        mappings=[],
        assessment=ExperienceAssessment(
            strengths=[], friction_points=[], ethics_warnings=[], opportunities=[],
        ),
        executive_summary="总结",
        meta=TeardownMeta(model="claude-opus-4-8", generated_at="2026-06-13"),
    )
    js = result.model_dump_json()
    assert "executive_summary" in js


def test_mapping_list_wraps_mappings():
    ml = MappingList(mappings=[])
    assert ml.mappings == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/pipeline/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.pipeline'`

- [ ] **Step 3: 实现 schemas**

`src/psyteardown/pipeline/__init__.py`: 空文件。
`src/psyteardown/pipeline/schemas.py`:
```python
"""流水线各步的输入/输出结构化模型,以及最终 TeardownResult。"""

from pydantic import BaseModel, Field


# --- Step 1 输出 ---
class Feature(BaseModel):
    name: str
    description: str
    user_goal: str


class ProductProfile(BaseModel):
    name: str
    product_type: str
    one_liner: str
    features: list[Feature] = Field(default_factory=list)
    touchpoints: list[str] = Field(default_factory=list)


# --- Step 3 输出 ---
class Mapping(BaseModel):
    feature: str
    framework_id: str
    principle_id: str
    rationale: str
    evidence: str
    confidence: float
    error: str | None = None


class MappingList(BaseModel):
    """messages.parse 要求顶层为 object,用此包装一组 Mapping。"""

    mappings: list[Mapping] = Field(default_factory=list)


# --- Step 4 输出 ---
class ExperienceAssessment(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    friction_points: list[str] = Field(default_factory=list)
    ethics_warnings: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


# --- Step 5 输出包装 ---
class Synthesis(BaseModel):
    executive_summary: str


# --- 最终结果 ---
class TeardownMeta(BaseModel):
    model: str
    generated_at: str
    elapsed_seconds: float = 0.0


class TeardownResult(BaseModel):
    product: ProductProfile
    frameworks_used: list[str] = Field(default_factory=list)
    mappings: list[Mapping] = Field(default_factory=list)
    assessment: ExperienceAssessment
    executive_summary: str
    meta: TeardownMeta
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/pipeline/test_schemas.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/__init__.py src/psyteardown/pipeline/schemas.py tests/pipeline/__init__.py tests/pipeline/test_schemas.py
git commit -m "feat: add pipeline schemas"
```

---

## Task 9: 流水线 5 步函数

**Files:**
- Create: `src/psyteardown/pipeline/steps.py`
- Test: `tests/pipeline/test_steps.py`

> 说明:每步是纯函数,LLM 调用通过注入的 provider 完成。Step2 无 LLM。Step3 逐功能调用,单功能失败标 `error` 并继续。

- [ ] **Step 1: 写失败测试**

`tests/pipeline/test_steps.py`:
```python
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider, LLMError
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _fw(id_, tags):
    return Framework(
        id=id_, name=id_, category="motivation", summary="s", tags=tags,
        principles=[Principle(id="p", name="p", description="d", look_for=["x"])],
        references=["r"],
    )


def _profile():
    return ProductProfile(
        name="Demo", product_type="App", one_liner="x",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=["推送"],
    )


def test_step1_parse_product():
    provider = FakeProvider(structured_responses=[_profile()])
    profile = steps.parse_product(provider, "一些产品描述文本")
    assert profile.name == "Demo"
    assert "一些产品描述文本" in provider.calls[0]["prompt"]


def test_step2_retrieve_is_pure_no_llm():
    provider = FakeProvider()  # 空队列;若 step2 调 LLM 会抛错
    library = [_fw("habit", ["习惯养成", "推送"]), _fw("pricing", ["定价"])]
    frameworks = steps.retrieve(_profile(), library, top_n=1)
    assert frameworks[0].id == "habit"
    assert provider.calls == []  # 确认未触 LLM


def test_step3_maps_each_feature():
    mapping = Mapping(
        feature="签到", framework_id="habit", principle_id="p",
        rationale="r", evidence="e", confidence=0.9,
    )
    provider = FakeProvider(structured_responses=[MappingList(mappings=[mapping])])
    mappings = steps.map_features(provider, _profile(), [_fw("habit", ["习惯养成"])])
    assert mappings[0].feature == "签到"


def test_step3_failure_marks_error_and_continues():
    # 队列耗尽 → 该次映射失败,应返回带 error 的占位 mapping 而非崩溃
    provider = FakeProvider(structured_responses=[])
    mappings = steps.map_features(provider, _profile(), [_fw("habit", ["习惯养成"])])
    assert len(mappings) == 1
    assert mappings[0].error is not None


def test_step4_assess_experience():
    assessment = ExperienceAssessment(
        strengths=["强"], friction_points=["阻"], ethics_warnings=["伦"], opportunities=["机"],
    )
    provider = FakeProvider(structured_responses=[assessment])
    out = steps.assess_experience(provider, _profile(), [])
    assert out.strengths == ["强"]


def test_step5_synthesize():
    provider = FakeProvider(structured_responses=[Synthesis(executive_summary="总结文本")])
    summary = steps.synthesize(provider, _profile(), [], ExperienceAssessment())
    assert summary == "总结文本"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/pipeline/test_steps.py -v`
Expected: FAIL — `AttributeError: module 'psyteardown.pipeline.steps' has no attribute ...` 或 ModuleNotFoundError

- [ ] **Step 3: 实现 5 步**

`src/psyteardown/pipeline/steps.py`:
```python
"""拆解流水线 5 步。每步:输入 → 输出;LLM 调用经注入的 provider。"""

from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMError, LLMProvider
from psyteardown.pipeline.schemas import (
    ExperienceAssessment,
    Mapping,
    MappingList,
    ProductProfile,
    Synthesis,
)
from psyteardown.kb.retriever import retrieve_frameworks

_SYSTEM = "你是资深产品体验与行为心理学分析师。只依据给定框架做拆解,不要编造心理学理论。"


def parse_product(provider: LLMProvider, description: str) -> ProductProfile:
    """Step 1:把自由文本归一成结构化产品画像(不涉及心理学)。"""
    prompt = (
        "请把下面的产品描述解析成结构化画像:产品名、类型、一句话定位、"
        "核心功能列表(每个含名称/描述/用户目标)、关键体验触点。\n\n"
        f"产品描述:\n{description}"
    )
    return provider.structured_complete(prompt, ProductProfile, system=_SYSTEM)


def retrieve(
    profile: ProductProfile, library: list[Framework], top_n: int = 5
) -> list[Framework]:
    """Step 2:纯代码,按产品类型/功能/触点关键词检索相关框架。"""
    keywords = [profile.product_type, *profile.touchpoints]
    keywords += [f.name for f in profile.features]
    return retrieve_frameworks(library, keywords=keywords, top_n=top_n)


def _frameworks_brief(frameworks: list[Framework]) -> str:
    lines = []
    for fw in frameworks:
        ps = "; ".join(
            f"{p.id}:{p.name}(线索:{'/'.join(p.look_for)})" for p in fw.principles
        )
        lines.append(f"- [{fw.id}] {fw.name} — {fw.summary} 原则: {ps}")
    return "\n".join(lines)


def map_features(
    provider: LLMProvider,
    profile: ProductProfile,
    frameworks: list[Framework],
) -> list[Mapping]:
    """Step 3:逐功能/触点映射到框架原则。单项失败标 error 并继续。"""
    brief = _frameworks_brief(frameworks)
    valid_ids = ", ".join(fw.id for fw in frameworks)
    targets = [f.name for f in profile.features] + profile.touchpoints
    mappings: list[Mapping] = []
    for target in targets:
        prompt = (
            f"可用心理学框架:\n{brief}\n\n"
            f"产品「{profile.name}」的功能/触点:「{target}」。\n"
            "请判断它用到了哪个框架的哪条原则、在产品中的具体体现、为何有效,"
            "并给出 0-1 的置信度。framework_id 必须来自这些 id: "
            f"{valid_ids}。若适用多条,返回最贴切的若干条 mapping。"
        )
        try:
            result = provider.structured_complete(prompt, MappingList, system=_SYSTEM)
            mappings.extend(result.mappings)
        except LLMError as e:
            mappings.append(
                Mapping(
                    feature=target, framework_id="", principle_id="",
                    rationale="", evidence="", confidence=0.0, error=str(e),
                )
            )
    return mappings


def assess_experience(
    provider: LLMProvider,
    profile: ProductProfile,
    mappings: list[Mapping],
) -> ExperienceAssessment:
    """Step 4:整体体验评估 + 暗黑模式/伦理标注。"""
    mapping_lines = "\n".join(
        f"- {m.feature}: {m.framework_id}.{m.principle_id} — {m.evidence}"
        for m in mappings
        if not m.error
    )
    prompt = (
        f"产品:{profile.name}({profile.one_liner})。\n"
        f"已识别的心理学机制:\n{mapping_lines}\n\n"
        "请给出整体体验评估:优势、摩擦点、伦理/暗黑模式警示、机会点。"
    )
    return provider.structured_complete(prompt, ExperienceAssessment, system=_SYSTEM)


def synthesize(
    provider: LLMProvider,
    profile: ProductProfile,
    mappings: list[Mapping],
    assessment: ExperienceAssessment,
) -> str:
    """Step 5:综合成 executive summary。"""
    prompt = (
        f"产品:{profile.name}。优势:{assessment.strengths};"
        f"摩擦:{assessment.friction_points};伦理警示:{assessment.ethics_warnings}。\n"
        "请写一段简洁的高管摘要(executive summary),概述该产品的心理学拆解结论。"
    )
    return provider.structured_complete(prompt, Synthesis, system=_SYSTEM).executive_summary
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/pipeline/test_steps.py -v`
Expected: PASS(6 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/steps.py tests/pipeline/test_steps.py
git commit -m "feat: add pipeline steps (parse/retrieve/map/assess/synthesize)"
```

---

## Task 10: 编排器

**Files:**
- Create: `src/psyteardown/pipeline/orchestrator.py`
- Test: `tests/pipeline/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

`tests/pipeline/test_orchestrator.py`:
```python
from psyteardown.kb.models import Framework, Principle
from psyteardown.llm.base import FakeProvider
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, MappingList, ExperienceAssessment, Synthesis,
)


def _library():
    return [
        Framework(
            id="habit", name="上瘾模型", category="habit", summary="s",
            tags=["签到", "习惯养成"],
            principles=[Principle(id="trigger", name="触发", description="d", look_for=["推送"])],
            references=["r"],
        )
    ]


def test_run_teardown_full_pipeline():
    profile = ProductProfile(
        name="Demo", product_type="App", one_liner="每日签到App",
        features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
        touchpoints=["推送"],
    )
    mapping = Mapping(
        feature="签到", framework_id="habit", principle_id="trigger",
        rationale="r", evidence="e", confidence=0.9,
    )
    # 队列顺序:step1 profile → step3 两次(签到 + 推送触点)→ step4 → step5
    provider = FakeProvider(structured_responses=[
        profile,
        MappingList(mappings=[mapping]),
        MappingList(mappings=[]),
        ExperienceAssessment(strengths=["强"], friction_points=[], ethics_warnings=["伦"], opportunities=[]),
        Synthesis(executive_summary="总结"),
    ])

    result = run_teardown(
        provider, "每日签到App描述", library=_library(),
        generated_at="2026-06-13", top_n=5,
    )

    assert result.product.name == "Demo"
    assert result.executive_summary == "总结"
    assert "habit" in result.frameworks_used
    assert result.assessment.ethics_warnings == ["伦"]
    assert result.meta.model == "fake"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/pipeline/test_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.pipeline.orchestrator'`

- [ ] **Step 3: 实现编排器**

`src/psyteardown/pipeline/orchestrator.py`:
```python
"""编排 5 步流水线,产出 TeardownResult。"""

from psyteardown.kb.models import Framework
from psyteardown.llm.base import LLMProvider
from psyteardown.llm.claude import DEFAULT_MODEL
from psyteardown.pipeline import steps
from psyteardown.pipeline.schemas import TeardownMeta, TeardownResult


def run_teardown(
    provider: LLMProvider,
    description: str,
    library: list[Framework],
    *,
    generated_at: str,
    model_label: str | None = None,
    top_n: int = 5,
) -> TeardownResult:
    """跑完整流水线。generated_at 由调用方传入(脚本环境禁用 datetime.now)。"""
    profile = steps.parse_product(provider, description)
    frameworks = steps.retrieve(profile, library, top_n=top_n)
    mappings = steps.map_features(provider, profile, frameworks)
    assessment = steps.assess_experience(provider, profile, mappings)
    summary = steps.synthesize(provider, profile, mappings, assessment)

    return TeardownResult(
        product=profile,
        frameworks_used=[fw.id for fw in frameworks],
        mappings=mappings,
        assessment=assessment,
        executive_summary=summary,
        meta=TeardownMeta(
            model=model_label or _provider_label(provider),
            generated_at=generated_at,
        ),
    )


def _provider_label(provider: LLMProvider) -> str:
    """从 provider 取一个可读模型标签;FakeProvider → 'fake'。"""
    cls = type(provider).__name__
    if cls == "ClaudeProvider":
        return getattr(provider, "_model", DEFAULT_MODEL)
    return "fake"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/pipeline/test_orchestrator.py -v`
Expected: PASS(1 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/pipeline/orchestrator.py tests/pipeline/test_orchestrator.py
git commit -m "feat: add teardown orchestrator"
```

---

## Task 11: 报告渲染

**Files:**
- Create: `src/psyteardown/report/__init__.py`
- Create: `src/psyteardown/report/render.py`
- Test: `tests/report/test_render.py`

- [ ] **Step 1: 写失败测试**

`tests/report/__init__.py`: 空文件。
`tests/report/test_render.py`:
```python
import json

from psyteardown.pipeline.schemas import (
    ProductProfile, Feature, Mapping, ExperienceAssessment, TeardownResult, TeardownMeta,
)
from psyteardown.report.render import render_markdown, render_json


def _result():
    return TeardownResult(
        product=ProductProfile(
            name="Demo", product_type="App", one_liner="每日签到App",
            features=[Feature(name="签到", description="每日签到", user_goal="拿奖励")],
            touchpoints=["推送"],
        ),
        frameworks_used=["hook-model"],
        mappings=[
            Mapping(feature="签到", framework_id="hook-model", principle_id="trigger",
                    rationale="形成回访习惯", evidence="每日推送提醒", confidence=0.9),
            Mapping(feature="低置信项", framework_id="flow", principle_id="clear_goals",
                    rationale="r", evidence="e", confidence=0.3),
            Mapping(feature="坏项", framework_id="", principle_id="", rationale="",
                    evidence="", confidence=0.0, error="解析失败"),
        ],
        assessment=ExperienceAssessment(
            strengths=["回访强"], friction_points=["步骤多"],
            ethics_warnings=["可能滥用推送"], opportunities=["增加自定义"],
        ),
        executive_summary="这是一个依赖习惯回路的签到产品。",
        meta=TeardownMeta(model="claude-opus-4-8", generated_at="2026-06-13"),
    )


def test_render_json_is_valid_and_complete():
    data = json.loads(render_json(_result()))
    assert data["executive_summary"]
    assert data["frameworks_used"] == ["hook-model"]


def test_markdown_has_all_sections():
    md = render_markdown(_result())
    for heading in ["概述", "产品画像", "逐功能心理学拆解", "整体体验评估",
                    "伦理", "机会点", "附录"]:
        assert heading in md


def test_markdown_flags_low_confidence():
    md = render_markdown(_result())
    assert "⚠️" in md  # 低置信度(0.3)应被标注


def test_markdown_notes_failed_mapping():
    md = render_markdown(_result())
    assert "解析失败" in md  # 失败的映射如实呈现,不假装成功
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/report/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.report'`

- [ ] **Step 3: 实现渲染**

`src/psyteardown/report/__init__.py`: 空文件。
`src/psyteardown/report/render.py`:
```python
"""把 TeardownResult 渲染成 Markdown 或 JSON。"""

from psyteardown.pipeline.schemas import TeardownResult

LOW_CONFIDENCE = 0.5


def render_json(result: TeardownResult) -> str:
    return result.model_dump_json(indent=2)


def render_markdown(result: TeardownResult) -> str:
    p = result.product
    out: list[str] = []

    # 1. 概述
    out.append(f"# 心理学拆解报告:{p.name}\n")
    out.append("## 概述\n")
    out.append(f"**{p.one_liner}**\n")
    out.append(f"{result.executive_summary}\n")

    # 2. 产品画像
    out.append("## 产品画像\n")
    out.append(f"- 类型:{p.product_type}")
    out.append(f"- 关键触点:{', '.join(p.touchpoints) or '—'}")
    out.append("- 核心功能:")
    for f in p.features:
        out.append(f"  - **{f.name}** — {f.description}(用户目标:{f.user_goal})")
    out.append("")

    # 3. 逐功能心理学拆解
    out.append("## 逐功能心理学拆解\n")
    for m in result.mappings:
        if m.error:
            out.append(f"- ⚠️ **{m.feature}**:映射失败({m.error})")
            continue
        flag = " ⚠️低置信" if m.confidence < LOW_CONFIDENCE else ""
        out.append(
            f"- **{m.feature}** → `{m.framework_id}·{m.principle_id}`"
            f"(置信 {m.confidence:.2f}{flag})\n"
            f"  - 体现:{m.evidence}\n"
            f"  - 为何有效:{m.rationale}"
        )
    out.append("")

    # 4. 整体体验评估
    a = result.assessment
    out.append("## 整体体验评估\n")
    out.append(f"- 优势:{_join(a.strengths)}")
    out.append(f"- 摩擦点:{_join(a.friction_points)}")
    out.append("")

    # 5. 伦理 / 暗黑模式提示
    out.append("## ⚠️ 伦理 / 暗黑模式提示\n")
    if a.ethics_warnings:
        for w in a.ethics_warnings:
            out.append(f"- {w}")
    else:
        out.append("- 未发现明显风险")
    out.append("")

    # 6. 机会点
    out.append("## 机会点\n")
    for o in a.opportunities or ["—"]:
        out.append(f"- {o}")
    out.append("")

    # 7. 附录
    out.append("## 附录:引用框架\n")
    for fid in result.frameworks_used:
        out.append(f"- {fid}")
    out.append(f"\n_模型:{result.meta.model} · 生成时间:{result.meta.generated_at}_")

    return "\n".join(out)


def _join(items: list[str]) -> str:
    return "；".join(items) if items else "—"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/report/test_render.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交**

```bash
git add src/psyteardown/report/__init__.py src/psyteardown/report/render.py tests/report/__init__.py tests/report/test_render.py
git commit -m "feat: add report rendering (markdown/json)"
```

---

## Task 12: 薄 CLI

**Files:**
- Create: `src/psyteardown/cli.py`
- Test: `tests/test_cli.py`

> 说明:CLI 只做编排,无业务逻辑。`analyze` 默认用 `ClaudeProvider`;但测试通过 `--provider fake`(隐藏选项)注入 FakeProvider 以避免触网。时间戳在 CLI 层用 `datetime.now()` 注入(CLI 不是受 `Date.now` 限制的 workflow 脚本环境)。

- [ ] **Step 1: 写失败测试**

`tests/test_cli.py`:
```python
import json

from typer.testing import CliRunner

from psyteardown.cli import app

runner = CliRunner()


def test_kb_list_shows_frameworks():
    result = runner.invoke(app, ["kb", "list"])
    assert result.exit_code == 0
    assert "fogg-behavior-model" in result.stdout


def test_kb_show_one_framework():
    result = runner.invoke(app, ["kb", "show", "flow"])
    assert result.exit_code == 0
    assert "心流" in result.stdout


def test_kb_show_unknown_errors():
    result = runner.invoke(app, ["kb", "show", "nope"])
    assert result.exit_code != 0


def test_analyze_with_fake_provider_writes_json(tmp_path):
    src = tmp_path / "product.txt"
    src.write_text("一个每日签到App,有推送提醒。", encoding="utf-8")
    out = tmp_path / "result.json"
    result = runner.invoke(app, [
        "analyze", "--input", str(src), "--format", "json",
        "--out", str(out), "--provider", "fake",
    ])
    assert result.exit_code == 0, result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "executive_summary" in data


def test_analyze_empty_input_errors(tmp_path):
    src = tmp_path / "empty.txt"
    src.write_text("   ", encoding="utf-8")
    result = runner.invoke(app, [
        "analyze", "--input", str(src), "--provider", "fake",
    ])
    assert result.exit_code != 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'psyteardown.cli'`

- [ ] **Step 3: 实现 CLI**

`src/psyteardown/cli.py`:
```python
"""薄 CLI:读输入 → 调内核 → 写输出。零业务逻辑。"""

from datetime import datetime
from pathlib import Path

import typer

from psyteardown.kb.loader import load_frameworks
from psyteardown.llm.base import FakeProvider, LLMProvider
from psyteardown.pipeline.orchestrator import run_teardown
from psyteardown.report.render import render_json, render_markdown
from psyteardown.pipeline.schemas import (
    ProductProfile, MappingList, ExperienceAssessment, Synthesis,
)

app = typer.Typer(help="心理驱动型产品拆解 Agent(v1)")
kb_app = typer.Typer(help="知识库操作")
app.add_typer(kb_app, name="kb")


def _build_provider(name: str) -> LLMProvider:
    if name == "fake":
        # 仅用于测试:返回可跑通流水线的固定结构(无需真实 API)
        return FakeProvider(structured_responses=[
            ProductProfile(name="样例产品", product_type="App",
                           one_liner="自动生成的占位画像", features=[], touchpoints=[]),
            ExperienceAssessment(),  # 无功能/触点 → 无 step3 调用,直接 step4
            Synthesis(executive_summary="(fake provider 占位摘要)"),
        ])
    from psyteardown.llm.claude import ClaudeProvider

    return ClaudeProvider()


@app.command()
def analyze(
    input: Path = typer.Option(..., "--input", "-i", help="产品描述文本文件"),
    out: Path | None = typer.Option(None, "--out", "-o", help="输出文件;省略则打印到终端"),
    fmt: str = typer.Option("md", "--format", "-f", help="md 或 json"),
    provider: str = typer.Option("claude", "--provider", hidden=True),
):
    """拆解一个产品描述,输出结构化报告。"""
    text = input.read_text(encoding="utf-8").strip()
    if not text:
        typer.echo("错误:输入为空。", err=True)
        raise typer.Exit(code=1)

    library = load_frameworks()
    llm = _build_provider(provider)
    result = run_teardown(
        llm, text, library=library,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

    rendered = render_json(result) if fmt == "json" else render_markdown(result)
    if out:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"已写入 {out}")
    else:
        typer.echo(rendered)


@kb_app.command("list")
def kb_list():
    """列出已加载的框架。"""
    for fw in load_frameworks():
        typer.echo(f"{fw.id}\t{fw.name}\t({fw.category})")


@kb_app.command("show")
def kb_show(framework_id: str = typer.Argument(..., help="框架 id")):
    """查看某框架详情。"""
    for fw in load_frameworks():
        if fw.id == framework_id:
            typer.echo(f"# {fw.name} ({fw.id})\n{fw.summary}\n")
            for p in fw.principles:
                typer.echo(f"- {p.name}:{p.description}(线索:{', '.join(p.look_for)})")
            return
    typer.echo(f"未找到框架:{framework_id}", err=True)
    raise typer.Exit(code=1)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 端到端验证 CLI 可执行**

Run: `psyteardown kb list`
Expected: 列出 7 个框架(含 `fogg-behavior-model`)

- [ ] **Step 6: 提交**

```bash
git add src/psyteardown/cli.py tests/test_cli.py
git commit -m "feat: add thin CLI (analyze + kb commands)"
```

---

## Task 13: 可选端到端冒烟测试 + 全量回归

**Files:**
- Create: `tests/test_smoke_e2e.py`
- Create: `README.md`

> 说明:冒烟测试默认 **skip**,仅在设置了 `ANTHROPIC_API_KEY` 且显式开启 `PSYTEARDOWN_E2E=1` 时运行,验证真实 `ClaudeProvider` 跑通一次拆解。

- [ ] **Step 1: 写冒烟测试(默认跳过)**

`tests/test_smoke_e2e.py`:
```python
import os

import pytest

requires_e2e = pytest.mark.skipif(
    os.environ.get("PSYTEARDOWN_E2E") != "1" or not os.environ.get("ANTHROPIC_API_KEY"),
    reason="需要 PSYTEARDOWN_E2E=1 且配置 ANTHROPIC_API_KEY",
)


@requires_e2e
def test_real_claude_teardown():
    from datetime import datetime

    from psyteardown.kb.loader import load_frameworks
    from psyteardown.llm.claude import ClaudeProvider
    from psyteardown.pipeline.orchestrator import run_teardown

    result = run_teardown(
        ClaudeProvider(),
        "一个每日英语单词打卡 App,有连续打卡天数、推送提醒、好友排行榜、限时挑战。",
        library=load_frameworks(),
        generated_at=datetime.now().strftime("%Y-%m-%d"),
    )
    assert result.product.name
    assert result.executive_summary
    assert result.frameworks_used
```

- [ ] **Step 2: 确认冒烟测试被跳过(无 key 环境)**

Run: `pytest tests/test_smoke_e2e.py -v`
Expected: SKIPPED(1 skipped)

- [ ] **Step 3: 写 README**

`README.md`:
```markdown
# psyteardown — 心理驱动型产品拆解 Agent(v1)

基于精选心理学框架知识库,把产品文字描述拆解成结构化报告(Markdown / JSON)。

## 安装

    pip install -e ".[dev]"

## 用法

    export ANTHROPIC_API_KEY=sk-ant-...
    psyteardown analyze --input product.txt --format md  --out report.md
    psyteardown analyze --input product.txt --format json --out result.json
    psyteardown kb list
    psyteardown kb show fogg-behavior-model

## 测试

    pytest                       # 全量(冒烟测试默认跳过,不触网)
    PSYTEARDOWN_E2E=1 pytest      # 含真实 Claude 端到端冒烟(需 ANTHROPIC_API_KEY)

## 架构

库内核分四子系统:kb(知识库)、pipeline(5 步拆解流水线)、llm(可插拔 provider,默认 Claude)、report(渲染)。CLI 仅为薄入口。

v1 范围与后续规划见 `docs/superpowers/specs/2026-06-13-psychology-product-teardown-agent-design.md`。
```

- [ ] **Step 4: 全量回归**

Run: `pytest -v`
Expected: 所有测试通过,1 个 e2e 测试 skipped

- [ ] **Step 5: 提交**

```bash
git add tests/test_smoke_e2e.py README.md
git commit -m "test: add optional e2e smoke test; add README"
```

---

## 自检:spec 覆盖核对

- 种子知识库(精选框架,YAML) → Task 2/3/4 ✅
- 拆解引擎多步流水线(方案 B,5 步) → Task 8/9/10 ✅
- 结构化报告(Markdown + JSON,7 节,出处+置信度+伦理单列) → Task 11 ✅
- 库核心 + 薄 CLI → Task 12 ✅
- 可插拔 LLM provider(默认 Claude) → Task 6/7 ✅
- 文字为主输入 + 预留扩展点(retriever 接口、provider 接口) → Task 5/6 ✅
- 错误处理(空输入、单功能失败标 error 不中断、provider 重试、缺 key 提示) → Task 9/12/7 ✅
- 测试可脱离真实 LLM(FakeProvider) + 可选 e2e 冒烟 → Task 6/9/10/13 ✅
- YAGNI 不做项(抓取/多模态/向量/沉淀/API/聊天/Skill) → 计划未涉及,接口已预留 ✅
```
