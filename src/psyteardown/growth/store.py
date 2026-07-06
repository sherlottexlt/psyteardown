"""候选/习得框架的 YAML 存储。候选待审;approve 后写习得层供 loader 合并。"""

from pathlib import Path

import yaml

from psyteardown.growth.models import FrameworkCandidate


class GrowthError(Exception):
    """候选/习得读写错误。"""


class GrowthStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._candidates = self.root / "candidates"
        self._learned = self.root / "learned"
        self._candidates.mkdir(parents=True, exist_ok=True)
        self._learned.mkdir(parents=True, exist_ok=True)

    def learned_dir(self) -> Path:
        return self._learned

    def save_candidate(self, cand: FrameworkCandidate) -> None:
        path = self._candidates / f"{cand.framework.id}.yaml"
        path.write_text(
            yaml.safe_dump(cand.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def list_candidates(self) -> list[FrameworkCandidate]:
        out: list[FrameworkCandidate] = []
        for p in sorted(self._candidates.glob("*.yaml")):
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
            out.append(FrameworkCandidate.model_validate(raw))
        return out

    def get_candidate(self, fid: str) -> FrameworkCandidate | None:
        p = self._candidates / f"{fid}.yaml"
        if not p.is_file():
            return None
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        return FrameworkCandidate.model_validate(raw)

    def approve(self, fid: str) -> Path:
        cand = self.get_candidate(fid)
        if cand is None:
            raise GrowthError(f"候选不存在: {fid}")
        dest = self._learned / f"{fid}.yaml"
        dest.write_text(
            yaml.safe_dump(cand.framework.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (self._candidates / f"{fid}.yaml").unlink()
        return dest

    def reject(self, fid: str) -> None:
        p = self._candidates / f"{fid}.yaml"
        if not p.is_file():
            raise GrowthError(f"候选不存在: {fid}")
        p.unlink()
