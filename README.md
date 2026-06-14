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
