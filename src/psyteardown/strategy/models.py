"""程序性记忆:拆解策略卡。"""

from pydantic import BaseModel, Field


class StrategyCard(BaseModel):
    id: str                                   # kebab-case,唯一;做文件名
    rule: str                                 # 启发式本身
    rationale: str                            # 依据(从哪些案例规律归纳)
    target_step: str                          # retrieval | mapping | assessment
    applies_to: list[str] = Field(default_factory=list)      # 品类命中词;空=通配
    source_case_ids: list[str] = Field(default_factory=list) # 支撑案例(复盘可空)
    created_at: str = ""                      # 调用方注入


class CardList(BaseModel):
    """messages.parse 顶层需 object。"""

    cards: list[StrategyCard] = Field(default_factory=list)
