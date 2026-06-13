"""从 YAML 文件加载并校验心理学框架知识库。"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from psyteardown.kb.models import Framework

# 随包分发的种子知识库目录
DEFAULT_KB_DIR = Path(__file__).parent.parent / "data" / "frameworks"


class KBLoadError(Exception):
    """加载或校验知识库失败。"""


def load_frameworks(directory: Path | None = None) -> list[Framework]:
    """加载目录下所有 *.yaml 框架,按 id 升序返回。坏文件/坏 schema 抛 KBLoadError。"""
    directory = directory or DEFAULT_KB_DIR
    if not directory.is_dir():
        raise KBLoadError(f"知识库目录不存在: {directory}")

    frameworks: list[Framework] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise KBLoadError(f"YAML 解析失败 {path.name}: {e}") from e
        try:
            frameworks.append(Framework.model_validate(raw))
        except ValidationError as e:
            raise KBLoadError(f"框架校验失败 {path.name}: {e}") from e

    frameworks.sort(key=lambda f: f.id)
    return frameworks
