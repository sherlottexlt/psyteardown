"""单案例自评的数据模型(元认知第二块)。"""

from pydantic import BaseModel, Field


class CaseReview(BaseModel):
    score: float = Field(ge=0, le=1)                       # 0-1 总体质量分
    strengths: list[str] = Field(default_factory=list)     # 亮点:拆得好的地方
    weaknesses: list[str] = Field(default_factory=list)    # 缺陷:置信虚高/证据薄弱/疑似遗漏
    suggestions: list[str] = Field(default_factory=list)   # 改进建议(可喂 reflect 管道)
    reviewed_at: str = ""                                  # 调用方注入
    model: str = ""                                        # 自评用的模型标签
