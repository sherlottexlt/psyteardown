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
