"""
Pydantic contracts and schemas for FinSight AI.
Strictly models input requests, agent intermediate state, numeric facts/provenance,
citations, and final output contracts per blueprint specifications.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

class Citation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    document_id: str
    title: str
    page: Optional[int] = None
    section: Optional[str] = None
    source_url: HttpUrl

    @field_validator('document_id', 'title')
    @classmethod
    def required_citation_text(cls, value: str) -> str:
        if not value:
            raise ValueError('Citation identifiers and titles must not be empty.')
        return value

class NumericClaim(BaseModel):
    value: Union[Decimal, float, int]
    unit: str
    period: str
    source_id: str
    as_of: datetime
    tool_run_id: Optional[str] = None

    @field_validator('source_id', 'unit', 'period')
    @classmethod
    def numeric_claim_provenance_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Numeric claims require a source, unit, and period.')
        return value

    @field_validator('value', mode='before')
    def validate_value(cls, v):
        if isinstance(v, (float, int, str)):
            try:
                return Decimal(str(v))
            except Exception:
                return Decimal(0)
        return v

class NumericFact(BaseModel):
    fact_id: str
    metric: str
    value: Union[Decimal, float, int]
    display_value: str
    unit: str
    period_or_observation_date: str
    source_name: str
    source_url_or_document_id: str
    source_locator: Optional[str] = None
    fetched_at: datetime
    freshness: Literal["current", "delayed", "stale", "historical"] = "historical"
    calculation: Optional[Dict[str, Any]] = None  # {formula, operand_fact_ids, tool_run_id}

class ToolResult(BaseModel):
    tool_name: str
    tool_run_id: str
    status: Literal["success", "error", "skipped"]
    duration_ms: float
    data: Any
    facts: List[NumericFact] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    error_message: Optional[str] = None
    source_attribution: Optional[str] = None
    as_of: Optional[str] = None
    freshness: Literal["current", "delayed", "stale", "historical"] = "current"

class AnswerDraft(BaseModel):
    answer_text: str
    citations: List[Citation] = Field(default_factory=list)
    numeric_claims: List[NumericClaim] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    safety_label: Literal["factual_research", "refusal", "clarification"] = "factual_research"

    @field_validator('answer_text')
    @classmethod
    def answer_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Answer text must not be empty.')
        return value

class AskRequest(BaseModel):
    session_id: Optional[str] = None
    company_id: Optional[int] = None
    symbol: Optional[str] = None
    question: str = Field(min_length=1, max_length=16000)
    as_of_preference: Literal["latest_available", "historical", "strict_realtime"] = "latest_available"
    language: Literal["en", "hi"] = "en"

    @field_validator('question')
    @classmethod
    def question_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Question must not be empty.')
        return value

    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().upper()
        return value or None

class AskResponse(BaseModel):
    trace_id: str
    session_id: str
    question: str
    answer: str
    safety_label: Literal["factual_research", "refusal", "clarification"]
    citations: List[Citation] = Field(default_factory=list)
    numeric_claims: List[NumericClaim] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    data_freshness: Literal["current", "delayed", "stale", "historical"] = "historical"
    prompt_version: str = "v1.2-grounded"
    tool_trace: List[Dict[str, Any]] = Field(default_factory=list)
    latency_breakdown_ms: Dict[str, float] = Field(default_factory=dict)
    tokens_used: Optional[int] = 0

class AgentState(BaseModel):
    trace_id: str
    user_id: str = "default_user"
    session_id: str
    query: str
    language: Literal["en", "hi"] = "en"
    as_of_preference: Literal["latest_available", "historical", "strict_realtime"] = "latest_available"
    intent: Literal[
        "filing_qa",
        "metric",
        "calculation",
        "market_history",
        "announcement",
        "advice_refusal",
        "clarification",
        "portfolio_analysis"
    ] = "filing_qa"
    company_id: Optional[int] = None
    company_symbol: Optional[str] = None
    company_name: Optional[str] = None
    fiscal_period: Optional[str] = None
    evidence: List[Citation] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    numeric_facts: List[NumericFact] = Field(default_factory=list)
    draft: Optional[AnswerDraft] = None
    final_response: Optional[AskResponse] = None
    safety_status: Literal["pass", "refuse", "review"] = "pass"
    safety_reason: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    latencies: Dict[str, float] = Field(default_factory=dict)
    tokens_used: int = 0
    model_config = ConfigDict(arbitrary_types_allowed=True)

class HoldingItem(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    shares: Union[Decimal, float, int]
    avg_price: Union[Decimal, float, int]
    current_price: Optional[Union[Decimal, float, int]] = None
    current_value: Optional[Union[Decimal, float, int]] = None
    sector: Optional[str] = "Diversified"

class SectorConcentration(BaseModel):
    sector: str
    value: Union[Decimal, float]
    percentage: Union[Decimal, float]

class PortfolioAnalysisResult(BaseModel):
    total_portfolio_value: Union[Decimal, float]
    holdings_count: int
    sector_breakdown: List[SectorConcentration]
    top_holdings: List[Dict[str, Any]]
    calculation_lineage: List[str]
    disclaimer: str = (
        "FinSight AI portfolio analysis provides deterministic sector and concentration "
        "calculations for historical research only. It does not provide buy/sell advice or suitability assessment."
    )
