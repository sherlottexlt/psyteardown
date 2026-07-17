"""server 装配测试:需要 mcp 包(未装则整文件跳过)。"""

import asyncio

import pytest

pytest.importorskip("mcp")


def test_build_server_registers_six_tools():
    from psyteardown.mcp_server.server import build_server

    srv = build_server()
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert names == {"teardown", "similar", "review_case",
                     "kb_list", "kb_show", "memory_stats"}


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
