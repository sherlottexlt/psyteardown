"""案例库:单文件 SQLite,存案例 JSON + float32 向量 blob + 元数据。"""

import sqlite3
from pathlib import Path

import numpy as np

from psyteardown.memory.models import Case


class MemoryStoreError(Exception):
    """案例库读写或一致性错误。"""  # 注意:不用内置名 MemoryError


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id      TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    dim          INTEGER NOT NULL,
    embedding    BLOB NOT NULL,
    case_json    TEXT NOT NULL
)
"""


class CaseStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def save(self, case: Case, embedding: list[float]) -> None:
        arr = np.asarray(embedding, dtype=np.float32)
        self._conn.execute(
            "INSERT OR REPLACE INTO cases "
            "(case_id, product_name, created_at, dim, embedding, case_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (case.case_id, case.product_name, case.created_at,
             int(arr.shape[0]), arr.tobytes(), case.model_dump_json()),
        )
        self._conn.commit()

    def all(self) -> list[tuple[Case, list[float]]]:
        rows = self._conn.execute(
            "SELECT case_json, embedding FROM cases"
        ).fetchall()
        out: list[tuple[Case, list[float]]] = []
        for case_json, blob in rows:
            case = Case.model_validate_json(case_json)
            vec = np.frombuffer(blob, dtype=np.float32).tolist()
            out.append((case, vec))
        return out

    def get(self, case_id: str) -> Case | None:
        row = self._conn.execute(
            "SELECT case_json FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0])
