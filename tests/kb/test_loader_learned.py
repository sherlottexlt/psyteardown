from psyteardown.kb.loader import load_frameworks

SEED = """
id: seed-fw
name: 种子框架
category: motivation
summary: s
tags: [x]
principles:
  - id: p
    name: p
    description: d
    look_for: [a]
references: [r]
"""

LEARNED = """
id: learned-fw
name: 习得框架
category: habit
summary: s2
tags: [y]
principles:
  - id: q
    name: q
    description: d
    look_for: [b]
references: [r2]
"""

# 与种子同 id,应被跳过(种子优先)
CLASH = SEED.replace("种子框架", "冒充者")


def _write(d, name, text):
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def test_no_learned_dir_matches_v1(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "seed-fw.yaml", SEED)
    fws = load_frameworks(seed)
    assert [f.id for f in fws] == ["seed-fw"]


def test_merges_learned(tmp_path):
    seed = tmp_path / "seed"
    learned = tmp_path / "learned"
    _write(seed, "seed-fw.yaml", SEED)
    _write(learned, "learned-fw.yaml", LEARNED)
    fws = load_frameworks(seed, learned_dir=learned)
    assert {f.id for f in fws} == {"seed-fw", "learned-fw"}


def test_seed_wins_on_id_clash(tmp_path):
    seed = tmp_path / "seed"
    learned = tmp_path / "learned"
    _write(seed, "seed-fw.yaml", SEED)
    _write(learned, "seed-fw.yaml", CLASH)     # 同 id
    fws = load_frameworks(seed, learned_dir=learned)
    got = [f for f in fws if f.id == "seed-fw"][0]
    assert got.name == "种子框架"              # 种子优先,冒充者被跳过
    assert len(fws) == 1


def test_missing_learned_dir_is_ok(tmp_path):
    seed = tmp_path / "seed"
    _write(seed, "seed-fw.yaml", SEED)
    fws = load_frameworks(seed, learned_dir=tmp_path / "nope")   # 不存在 → 忽略
    assert [f.id for f in fws] == ["seed-fw"]
