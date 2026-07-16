"""情景记忆的案例模型。"""

import hashlib

from pydantic import BaseModel, Field

from psyteardown.pipeline.schemas import TeardownResult
from psyteardown.review.models import CaseReview


def case_id_for(description: str) -> str:
    """案例 id = 原始描述的 sha256 前 16 位(同描述复跑 → 同 id → upsert 去重)。"""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:16]


class Case(BaseModel):
    case_id: str
    product_name: str
    product_type: str
    one_liner: str
    frameworks_used: list[str] = Field(default_factory=list)
    description: str           # 被嵌入的原始产品描述(可追溯、可重算向量)
    result: TeardownResult     # v1 完整产物,原样嵌套
    created_at: str            # 调用方注入
    review: CaseReview | None = None   # v5 单案例自评;旧数据自动 None

    @classmethod
    def from_result(
        cls, result: TeardownResult, description: str, created_at: str
    ) -> "Case":
        return cls(
            case_id=case_id_for(description),
            product_name=result.product.name,
            product_type=result.product.product_type,
            one_liner=result.product.one_liner,
            frameworks_used=result.frameworks_used,
            description=description,
            result=result,
            created_at=created_at,
        )
