"""策略卡的 YAML 存储:候选待审;approve 后写已批准层供注入。仿 v3 GrowthStore。"""

import re
from pathlib import Path

import yaml

from psyteardown.strategy.models import StrategyCard

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class StrategyError(Exception):
    """策略卡读写或一致性错误。"""


def _check_id(sid: str) -> str:
    if not _ID_RE.match(sid):
        raise StrategyError(f"非法策略 id(仅允许字母/数字/_/-): {sid!r}")
    return sid


class StrategyStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._candidates = self.root / "strategy_candidates"
        self._approved = self.root / "strategies"
        self._rejected = self.root / "strategies_rejected.txt"
        self._candidates.mkdir(parents=True, exist_ok=True)
        self._approved.mkdir(parents=True, exist_ok=True)

    def approved_dir(self) -> Path:
        return self._approved

    def _rejected_ids(self) -> set[str]:
        if not self._rejected.is_file():
            return set()
        return {ln.strip() for ln in self._rejected.read_text(encoding="utf-8").splitlines() if ln.strip()}

    def is_rejected(self, sid: str) -> bool:
        return sid in self._rejected_ids()

    def _read(self, path: Path) -> StrategyCard:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return StrategyCard.model_validate(raw)

    def save_candidate(self, card: StrategyCard) -> None:
        sid = _check_id(card.id)
        if self.is_rejected(sid):
            return
        (self._candidates / f"{sid}.yaml").write_text(
            yaml.safe_dump(card.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def list_candidates(self) -> list[StrategyCard]:
        return [self._read(p) for p in sorted(self._candidates.glob("*.yaml"))]

    def list_approved(self) -> list[StrategyCard]:
        return [self._read(p) for p in sorted(self._approved.glob("*.yaml"))]

    def get_candidate(self, sid: str) -> StrategyCard | None:
        p = self._candidates / f"{sid}.yaml"
        return self._read(p) if p.is_file() else None

    def approve(self, sid: str) -> Path:
        _check_id(sid)
        card = self.get_candidate(sid)
        if card is None:
            raise StrategyError(f"候选不存在: {sid}")
        dest = self._approved / f"{sid}.yaml"
        dest.write_text(
            yaml.safe_dump(card.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (self._candidates / f"{sid}.yaml").unlink()
        return dest

    def reject(self, sid: str) -> None:
        _check_id(sid)
        p = self._candidates / f"{sid}.yaml"
        if not p.is_file():
            raise StrategyError(f"候选不存在: {sid}")
        p.unlink()
        with self._rejected.open("a", encoding="utf-8") as f:
            f.write(f"{sid}\n")
