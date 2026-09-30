"""
Fundamentals lookup tool.
Retrieves financial statement metrics (Revenue, Profit, Margins, Debt, EPS)
with source document lineage, period alignment, and provenanced facts.
"""
import uuid
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from schemas.contracts import ToolResult, NumericFact, Citation
from apps.observability.models import ToolRun
from apps.companies.models import Company, Security
from apps.market_data.models import MarketObservation
from apps.documents.models import Document

class FundamentalsLookupTool:
    @staticmethod
    def get_fundamentals(
        company_id_or_symbol: Any,
        metric: Optional[str] = None,
        period: Optional[str] = None,
        trace_id: str = ""
    ) -> ToolResult:
        start_time = time.time()
        tool_run_id = f"fund_{uuid.uuid4().hex[:8]}"
        facts: List[NumericFact] = []
        citations: List[Citation] = []

        try:
            # Resolve company
            company = None
            if isinstance(company_id_or_symbol, int) or (isinstance(company_id_or_symbol, str) and company_id_or_symbol.isdigit()):
                company = Company.objects.filter(id=int(company_id_or_symbol)).first()
            if not company and isinstance(company_id_or_symbol, str):
                sec = Security.objects.filter(symbol__iexact=company_id_or_symbol).select_related('company').first()
                if sec:
                    company = sec.company
                else:
                    company = Company.objects.filter(legal_name__icontains=company_id_or_symbol).first()

            if not company:
                duration_ms = (time.time() - start_time) * 1000
                return ToolResult(
                    tool_name="fundamentals_lookup",
                    tool_run_id=tool_run_id,
                    status="error",
                    duration_ms=duration_ms,
                    data=None,
                    error_message=f"Company '{company_id_or_symbol}' not found.",
                    source_attribution="Company Filings",
                    freshness="historical"
                )

            query = MarketObservation.objects.filter(
                company=company
            ).exclude(metric="close_price").select_related('source').order_by('-observed_at')

            if metric:
                # normalize metric name
                m_clean = metric.lower().replace(" ", "_")
                query = query.filter(metric__icontains=m_clean)

            if period:
                query = query.filter(period__iexact=period)

            obs_list = list(query[:20])

            # Also check related filing document
            doc_query = Document.objects.filter(company=company)
            if period:
                doc_query = doc_query.filter(fiscal_period__iexact=period)
            doc = doc_query.first()
            if doc:
                citations.append(Citation(
                    document_id=f"doc_{doc.id}",
                    title=doc.title,
                    section="Financial Statements",
                    source_url=doc.source_url
                ))

            data_list = []
            for obs in obs_list:
                fact = NumericFact(
                    fact_id=f"fact_fund_{obs.id}",
                    metric=obs.metric.replace("_", " ").title(),
                    value=obs.value_decimal,
                    display_value=f"{obs.value_decimal} {obs.unit}",
                    unit=obs.unit,
                    period_or_observation_date=obs.period,
                    source_name=obs.source.source_name if obs.source else "Audited Financial Report",
                    source_url_or_document_id=obs.source.source_url if obs.source else (doc.source_url if doc else "https://www.bseindia.com"),
                    source_locator=f"Period: {obs.period}",
                    fetched_at=obs.fetched_at if obs.fetched_at.tzinfo else obs.fetched_at.replace(tzinfo=timezone.utc),
                    freshness=obs.freshness
                )
                facts.append(fact)

                data_list.append({
                    "metric": obs.metric,
                    "metric_label": obs.metric.replace("_", " ").title(),
                    "value": str(obs.value_decimal),
                    "unit": obs.unit,
                    "period": obs.period,
                    "reported_at": obs.observed_at.strftime("%Y-%m-%d"),
                    "source": obs.source.source_name if obs.source else "Audited Financial Results",
                    "notes": obs.notes
                })

            duration_ms = (time.time() - start_time) * 1000

            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="fundamentals_lookup",
                    input_hash=f"{company.id}_{metric}_{period}",
                    status="success",
                    duration_ms=duration_ms,
                    source_id="financial_filings",
                    details={"company": company.legal_name, "count": len(data_list)}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="fundamentals_lookup",
                tool_run_id=tool_run_id,
                status="success",
                duration_ms=duration_ms,
                data={
                    "company_id": company.id,
                    "company_name": company.legal_name,
                    "fundamentals": data_list
                },
                facts=facts,
                citations=citations,
                source_attribution="SEBI / Stock Exchange Audited Financial Disclosures",
                as_of=obs_list[0].period if obs_list else (period or "Latest Reported"),
                freshness="historical"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="fundamentals_lookup",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=str(e),
                source_attribution="Financial Filings",
                freshness="historical"
            )
