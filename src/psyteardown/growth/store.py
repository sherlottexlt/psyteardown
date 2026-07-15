"""候选/习得框架的 YAML 存储。候选待审;approve 后写习得层供 loader 合并。"""

import re
from pathlib import Path

import yaml

from psyteardown.growth.models import FrameworkCandidate

# 框架 id 只允许字母/数字/下划线/连字符,防止 LLM 产出的 id 被当作路径("../evil")。
_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class GrowthError(Exception):
    """候选/习得读写错误。"""


def _check_id(fid: str) -> str:
    if not _ID_RE.match(fid):
        raise GrowthError(f"非法框架 id(仅允许字母/数字/_/-): {fid!r}")
    return fid


class GrowthStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._candidates = self.root / "candidates"
        self._learned = self.root / "learned"
        self._rejected = self.root / "rejected.txt"
        self._candidates.mkdir(parents=True, exist_ok=True)
        self._learned.mkdir(parents=True, exist_ok=True)

    def learned_dir(self) -> Path:
        return self._learned

    def _rejected_ids(self) -> set[str]:
        if not self._rejected.is_file():
            return set()
        return {
            ln.strip()
            for ln in self._rejected.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        }

    def is_rejected(self, fid: str) -> bool:
        return fid in self._rejected_ids()

    def save_candidate(self, cand: FrameworkCandidate) -> None:
        fid = _check_id(cand.framework.id)
        if self.is_rejected(fid):
            return  # 被驳回过的 id 不再复活
        path = self._candidates / f"{fid}.yaml"
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
        _check_id(fid)
        p = self._candidates / f"{fid}.yaml"
        if not p.is_file():
            return None
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        return FrameworkCandidate.model_validate(raw)

    def approve(self, fid: str) -> Path:
        _check_id(fid)
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
        _check_id(fid)
        p = self._candidates / f"{fid}.yaml"
        if not p.is_file():
            raise GrowthError(f"候选不存在: {fid}")
        p.unlink()
        # 记入驳回台账,防止下次 learn 复活同一 id
        with self._rejected.open("a", encoding="utf-8") as f:
            f.write(f"{fid}\n")
