"""server 装配测试:需要 mcp 包(未装则整文件跳过)。"""

import asyncio

import pytest

pytest.importorskip("mcp")


def test_build_server_registers_engineering_read_tools():
    from psyteardown.mcp_server.server import build_server

    srv = build_server()
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert names == {
        "teardown", "similar", "review_case", "kb_list", "kb_show",
        "memory_stats", "engineering_status", "engineering_traceability",
    }


def test_main_without_mcp_gives_install_hint(monkeypatch, capsys):
    import builtins

    from psyteardown.mcp_server import server

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError("No module named 'mcp'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code == 1
    assert "pip install" in capsys.readouterr().err


def test_guard_and_env_wiring_end_to_end(tmp_path, monkeypatch):
    """fake providers + tmp store:注册的工具真正跑通;_guard 把异常转错误文本。"""
    from psyteardown.mcp_server import server

    monkeypatch.setenv("PSYTEARDOWN_LLM", "fake")
    monkeypatch.setenv("PSYTEARDOWN_EMBED", "fake")
    monkeypatch.setenv("PSYTEARDOWN_STORE", str(tmp_path / "cases.db"))
    server._llm.cache_clear()
    server._embed_provider.cache_clear()

    srv = server.build_server()

    # mcp 1.28: FastMCP.call_tool → (list[TextContent], dict)
    out = asyncio.run(srv.call_tool("memory_stats", {}))
    assert out[0][0].text == "案例数:0"

    # review_case 对不存在的 id → 工具自身的错误文本(经 _guard 原样透传)
    out = asyncio.run(srv.call_tool("review_case", {"case_id": "nope"}))
    assert "案例不存在:nope" in out[0][0].text


def test_guard_converts_exception_to_text(tmp_path, monkeypatch):
    from psyteardown.mcp_server import server, tools as tools_mod

    monkeypatch.setenv("PSYTEARDOWN_LLM", "fake")
    monkeypatch.setenv("PSYTEARDOWN_EMBED", "fake")
    monkeypatch.setenv("PSYTEARDOWN_STORE", str(tmp_path / "cases.db"))
    server._llm.cache_clear()
    server._embed_provider.cache_clear()

    def _boom(*a, **k):
        raise RuntimeError("炸了")

    monkeypatch.setattr(tools_mod, "memory_stats_tool", _boom)
    srv = server.build_server()
    out = asyncio.run(srv.call_tool("memory_stats", {}))
    assert "错误:RuntimeError: 炸了" in out[0][0].text


def test_embed_provider_is_cached_singleton(monkeypatch):
    from psyteardown.mcp_server import server

    monkeypatch.setenv("PSYTEARDOWN_EMBED", "fake")
    server._embed_provider.cache_clear()
    assert server._embed() is server._embed()      # 同一实例(缓存生效)
