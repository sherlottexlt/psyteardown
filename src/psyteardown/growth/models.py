"""语义记忆增长:框架候选模型。"""

from pydantic import BaseModel, Field

from psyteardown.kb.models import Framework


class FrameworkCandidate(BaseModel):
    framework: Framework                              # 复用 v1 模型
    rationale: str                                    # 为什么现有框架盖不住
    source_case_ids: list[str] = Field(default_factory=list)
    created_at: str = ""                              # 调用方注入(LLM 无需提供)


class CandidateList(BaseModel):
    """messages.parse 顶层需 object。"""

    candidates: list[FrameworkCandidate] = Field(default_factory=list)
