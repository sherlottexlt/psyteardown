# psyteardown — 心理驱动型产品拆解 Agent(v3)

基于精选心理学框架知识库,把产品文字描述拆解成结构化报告(Markdown / JSON);
v2 起每次拆解可沉淀为案例,并用向量检索找相似历史案例(情景记忆)。

## 安装

    pip install -e ".[dev]"
    pip install -e ".[embed]"   # 可选:启用向量检索(本地嵌入模型,首次会下载)

## 用法

    export ANTHROPIC_API_KEY=sk-ant-...
    psyteardown analyze --input product.txt --format md  --out report.md
    psyteardown analyze --input product.txt --use-memory          # 注入相似历史案例
    psyteardown analyze --input product.txt --no-save             # 不落盘
    psyteardown similar --input product.txt --top-k 3             # 查相似历史案例
    psyteardown memory stats                                      # 案例库统计
    psyteardown learn                                            # 从案例提炼候选新框架(待审)
    psyteardown candidates list                                  # 列候选
    psyteardown candidates show <id>                             # 看候选详情
    psyteardown candidates approve <id>                          # 批准入库(此后 analyze 生效)
    psyteardown candidates reject <id>                           # 驳回
    psyteardown kb list
    psyteardown kb show fogg-behavior-model

案例库默认存于 `./.psyteardown/cases.db`(可用 `--store` 覆盖)。
向量检索默认用本地嵌入模型(需 `pip install -e ".[embed]"`,首次会下载模型);
若嵌入模型不可用(如离线),`analyze` 会跳过案例库并照常产出报告,不会失败。

## 测试

    pytest                       # 全量(冒烟测试默认跳过,不触网、不加载模型)
    PSYTEARDOWN_E2E=1 pytest      # 含真实 Claude + 本地嵌入冒烟

## 架构

- `kb` — 知识库(精选心理学框架,YAML)
- `pipeline` — 5 步拆解流水线
- `llm` — 可插拔 LLM provider(默认 Claude)
- `report` — Markdown / JSON 渲染
- `embed` — 可插拔嵌入 provider(默认本地 sentence-transformers)
- `memory` — 情景记忆:Case 模型、SQLite 案例库、向量检索
- `growth` — 语义记忆:从案例提炼候选新框架,人工审批后回填知识库(种子库永不被动)

CLI 仅为薄入口。设计与规划见 `docs/superpowers/specs/`(v1 + v2 设计文档)。
