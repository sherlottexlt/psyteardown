"""MCP server 装配:环境变量 → 依赖,FastMCP 注册 6 工具,stdio 传输。零业务逻辑。

mcp 包只在本模块内 import(可选依赖);tools.py 保持零 mcp 依赖。
"""

import os
import sys
from pathlib import Path

from psyteardown.mcp_server import tools


def _store() -> Path:
    return Path(os.environ.get("PSYTEARDOWN_STORE", str(tools.DEFAULT_STORE)))


def _llm():
    return tools.build_llm_provider(os.environ.get("PSYTEARDOWN_LLM", "claude"))


def _embed():
    return tools.build_embed_provider(os.environ.get("PSYTEARDOWN_EMBED", "local"))


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("psyteardown")

    def _guard(fn, *args, **kwargs) -> str:
        """统一错误壳:领域异常转清晰文本,不裸抛堆栈进对话。"""
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            return f"错误:{type(e).__name__}: {e}"

    @mcp.tool()
    def teardown(description: str, use_memory: bool = False,
                 use_strategies: bool = False, self_review: bool = False) -> str:
        """基于心理学框架拆解一个产品的文字描述,返回完整 Markdown 报告并落盘案例。
        当用户想分析/拆解某个产品的心理机制、成瘾设计、用户体验时使用。
        use_memory=检索相似历史案例注入;use_strategies=注入已批准策略卡;
        self_review=拆解后追加批判性自评。耗时可达数分钟,请耐心等待。"""
        return _guard(tools.teardown_tool, description, store=_store(),
                      llm=_llm(), embed_factory=_embed,
                      use_memory=use_memory, use_strategies=use_strategies,
                      self_review=self_review)

    @mcp.tool()
    def similar(description: str, top_k: int = 3) -> str:
        """按产品描述检索最相似的历史拆解案例(向量余弦)。"""
        return _guard(tools.similar_tool, description, top_k,
                      store=_store(), embed_factory=_embed)

    @mcp.tool()
    def review_case(case_id: str) -> str:
        """对指定 case_id 的历史案例补做批判性自评(覆盖旧自评)。"""
        return _guard(tools.review_case_tool, case_id,
                      store=_store(), llm=_llm())

    @mcp.tool()
    def kb_list() -> str:
        """列出心理学框架知识库(含已批准的习得框架)。"""
        return _guard(tools.kb_list_tool, store=_store())

    @mcp.tool()
    def kb_show(framework_id: str) -> str:
        """查看某个心理学框架的详情(原则 + 识别线索)。"""
        return _guard(tools.kb_show_tool, framework_id, store=_store())

    @mcp.tool()
    def memory_stats() -> str:
        """案例库统计(案例数)。"""
        return _guard(tools.memory_stats_tool, store=_store())

    return mcp


def main() -> None:
    try:
        import mcp  # noqa: F401
    except ImportError:
        print('未安装 mcp 包。请先安装:pip install -e ".[mcp]"', file=sys.stderr)
        raise SystemExit(1)
    build_server().run()          # stdio 传输(FastMCP 默认)
