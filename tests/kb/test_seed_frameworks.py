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
