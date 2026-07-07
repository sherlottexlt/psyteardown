"""从 YAML 文件加载并校验心理学框架知识库。"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from psyteardown.kb.models import Framework

# 随包分发的种子知识库目录
DEFAULT_KB_DIR = Path(__file__).parent.parent / "data" / "frameworks"


class KBLoadError(Exception):
    """加载或校验知识库失败。"""


def load_frameworks(
    directory: Path | None = None,
    *,
    learned_dir: Path | None = None,
) -> list[Framework]:
    """加载种子目录所有 *.yaml,按 id 升序返回;坏文件/坏 schema 抛 KBLoadError。
    若给 learned_dir 且存在,合并其中习得框架(与种子 id 冲突则跳过,种子优先)。"""
    directory = directory or DEFAULT_KB_DIR
    if not directory.is_dir():
        raise KBLoadError(f"知识库目录不存在: {directory}")

    frameworks: list[Framework] = []
    for path in sorted(directory.glob("*.yaml")):
        frameworks.append(_load_one(path))

    seed_ids = {f.id for f in frameworks}
    if learned_dir is not None and Path(learned_dir).is_dir():
        for path in sorted(Path(learned_dir).glob("*.yaml")):
            fw = _load_one(path)
            if fw.id in seed_ids:
                print(f"警告:习得框架 {fw.id} 与种子 id 冲突,已跳过(种子优先)。")
                continue
            frameworks.append(fw)

    frameworks.sort(key=lambda f: f.id)
    return frameworks


def _load_one(path: Path) -> Framework:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise KBLoadError(f"YAML 解析失败 {path.name}: {e}") from e
    try:
        return Framework.model_validate(raw)
    except ValidationError as e:
        raise KBLoadError(f"框架校验失败 {path.name}: {e}") from e
