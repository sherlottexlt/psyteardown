"""流水线各步的输入/输出结构化模型,以及最终 TeardownResult。"""

from pydantic import BaseModel, Field


# --- Step 1 输出 ---
class Feature(BaseModel):
    name: str
    description: str
    user_goal: str


class ProductProfile(BaseModel):
    name: str
    product_type: str
    one_liner: str
    features: list[Feature] = Field(default_factory=list)
    touchpoints: list[str] = Field(default_factory=list)


# --- Step 3 输出 ---
class Mapping(BaseModel):
    feature: str
    framework_id: str
    principle_id: str
    rationale: str
    evidence: str
    confidence: float
    error: str | None = None


class MappingList(BaseModel):
    """messages.parse 要求顶层为 object,用此包装一组 Mapping。"""

    mappings: list[Mapping] = Field(default_factory=list)


class GroundingStats(BaseModel):
    """step3 证据溯源记账。只统计参与校验的条目(m.error 为空者):
    kept + dropped = LLM 成功返回的映射总数,不含调用失败的占位条目。
    保留被丢弃条目全文,供事后归类「真编造」还是「改写误伤」(spec §8 标准 3)。"""

    kept: int = 0
    dropped: int = 0
    dropped_mappings: list[Mapping] = Field(default_factory=list)


# --- Step 4 输出 ---
class ExperienceAssessment(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    friction_points: list[str] = Field(default_factory=list)
    ethics_warnings: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


# --- Step 5 输出包装 ---
class Synthesis(BaseModel):
    executive_summary: str


# --- 最终结果 ---
class TeardownMeta(BaseModel):
    model: str
    generated_at: str
    elapsed_seconds: float = 0.0


class FrameworkCitation(BaseModel):
    """报告附录用:某框架的 id、名称与学术出处。"""

    id: str
    name: str
    references: list[str] = Field(default_factory=list)


class TeardownResult(BaseModel):
    product: ProductProfile
    frameworks_used: list[str] = Field(default_factory=list)
    citations: list[FrameworkCitation] = Field(default_factory=list)
    mappings: list[Mapping] = Field(default_factory=list)
    grounding: GroundingStats = Field(default_factory=GroundingStats)
    assessment: ExperienceAssessment
    executive_summary: str
    meta: TeardownMeta
