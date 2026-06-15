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
