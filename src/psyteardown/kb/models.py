"""知识库数据模型:心理学框架及其原则。"""

from pydantic import BaseModel, Field


class Principle(BaseModel):
    id: str
    name: str
    description: str
    look_for: list[str] = Field(default_factory=list)  # 拆解时的观察线索


class Framework(BaseModel):
    id: str
    name: str
    category: str  # motivation / persuasion / cognition / emotion / habit ...
    summary: str
    tags: list[str] = Field(default_factory=list)
    principles: list[Principle] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    ethics_notes: str | None = None
