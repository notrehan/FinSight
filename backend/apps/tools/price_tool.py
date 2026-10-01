"""
Price lookup tool.
Retrieves historical prices and Bhavcopy records with strict provenance,
timestamp metadata, source attribution, and explicit freshness classification.
"""
import uuid
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from schemas.contracts import ToolResult, NumericFact
from apps.observability.models import ToolRun
from apps.companies.models import Company, Security
from apps.market_data.models import MarketObservation

class PriceLookupTool:
    @staticmethod
    def get_prices(
        symbol_or_id: Any,
        exchange: Optional[str] = None,
        days: int = 5,
        trace_id: str = ""
    ) -> ToolResult:
        start_time = time.time()
        tool_run_id = f"price_{uuid.uuid4().hex[:8]}"
        facts: List[NumericFact] = []

        try:
            # Resolve security / company
            company = None
            security = None
            if isinstance(symbol_or_id, int) or (isinstance(symbol_or_id, str) and symbol_or_id.isdigit()):
                company = Company.objects.filter(id=int(symbol_or_id)).first()
                if company:
                    security = company.securities.first()
            
            if not security and isinstance(symbol_or_id, str):
                securities = Security.objects.filter(symbol__iexact=symbol_or_id)
                if exchange:
                    securities = securities.filter(exchange__iexact=exchange)
                security = securities.select_related('company').first()
                if security:
                    company = security.company

            if not security and not company:
                duration_ms = (time.time() - start_time) * 1000
                return ToolResult(
                    tool_name="price_lookup",
                    tool_run_id=tool_run_id,
                    status="error",
                    duration_ms=duration_ms,
                    data=None,
                    error_message=f"No security or company found matching '{symbol_or_id}'.",
                    source_attribution="NSE/BSE Bhavcopy Feed",
                    freshness="stale"
                )

            # Query observations for close_price
            query = MarketObservation.objects.filter(
                metric="close_price"
            ).select_related('source').order_by('-observed_at')

            if security:
                obs_list = list(query.filter(security=security)[:days])
            else:
                obs_list = list(query.filter(company=company)[:days])

            if not obs_list:
                duration_ms = (time.time() - start_time) * 1000
                return ToolResult(
                    tool_name="price_lookup",
                    tool_run_id=tool_run_id,
                    status="success",
                    duration_ms=duration_ms,
                    data={"symbol": security.symbol if security else company.legal_name, "prices": []},
                    error_message="No historical price observations available for this symbol.",
                    source_attribution="NSE/BSE Historical Bhavcopy",
                    freshness="historical"
                )

            now = datetime.now(timezone.utc)
            rows = []
            overall_freshness = "historical"

            for obs in obs_list:
                # Freshness check: if observed within 24 hours -> current, within 72 hours -> delayed, older -> historical / stale
                obs_utc = obs.observed_at if obs.observed_at.tzinfo else obs.observed_at.replace(tzinfo=timezone.utc)
                age_hours = (now - obs_utc).total_seconds() / 3600.0
                
                if age_hours <= 24:
                    freshness = "current"
                elif age_hours <= 72:
                    freshness = "delayed"
                else:
                    freshness = "historical"

                if freshness == "current" and overall_freshness == "historical":
                    overall_freshness = "current"

                fact = NumericFact(
                    fact_id=f"fact_price_{obs.id}",
                    metric="Closing Price",
                    value=obs.value_decimal,
                    display_value=f"INR {obs.value_decimal:,.2f}",
                    unit=obs.unit,
                    period_or_observation_date=obs.period or obs.observed_at.strftime("%Y-%m-%d"),
                    source_name=obs.source.source_name if obs.source else "NSE Daily Bhavcopy",
                    source_url_or_document_id=obs.source.source_url if obs.source else "https://www.nseindia.com",
                    source_locator=f"Trade Date: {obs.observed_at.strftime('%Y-%m-%d')}",
                    fetched_at=obs.fetched_at if obs.fetched_at.tzinfo else obs.fetched_at.replace(tzinfo=timezone.utc),
                    freshness=freshness
                )
                facts.append(fact)

                rows.append({
                    "date": obs.observed_at.strftime("%Y-%m-%d"),
                    "close_price": str(obs.value_decimal),
                    "unit": obs.unit,
                    "freshness": freshness,
                    "source": obs.source.source_name if obs.source else "NSE Daily Bhavcopy",
                    "source_attribution": obs.source.attribution_text if obs.source else "National Stock Exchange of India (NSE)"
                })

            duration_ms = (time.time() - start_time) * 1000

            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="price_lookup",
                    input_hash=str(symbol_or_id),
                    status="success",
                    duration_ms=duration_ms,
                    source_id="bhavcopy",
                    details={"count": len(rows), "symbol": security.symbol if security else ""}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="price_lookup",
                tool_run_id=tool_run_id,
                status="success",
                duration_ms=duration_ms,
                data={
                    "company_name": company.legal_name if company else "",
                    "symbol": security.symbol if security else "",
                    "exchange": security.exchange if security else "NSE",
                    "prices": rows
                },
                facts=facts,
                citations=[],
                source_attribution="NSE/BSE Daily Bhavcopy (Official Exchange Reports)",
                as_of=obs_list[0].observed_at.strftime("%Y-%m-%d"),
                freshness=overall_freshness
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="price_lookup",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=str(e),
                source_attribution="NSE/BSE Bhavcopy",
                freshness="stale"
            )
