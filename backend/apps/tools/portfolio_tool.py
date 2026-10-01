"""
Portfolio analyzer tool.
Performs deterministic sector concentration, holding value, and exposure calculations.
Strictly research & explanation only: enforces zero buy/sell/hold advice.
"""
import uuid
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any
from schemas.contracts import ToolResult, PortfolioAnalysisResult, SectorConcentration, NumericFact
from apps.companies.models import Security, Company
from apps.market_data.models import MarketObservation

class PortfolioAnalyzerTool:
    @staticmethod
    def analyze_holdings(holdings_raw: List[Dict[str, Any]], trace_id: str = "") -> ToolResult:
        start_time = time.time()
        tool_run_id = f"port_{uuid.uuid4().hex[:8]}"

        try:
            total_value = Decimal(0)
            sector_totals: Dict[str, Decimal] = {}
            processed_holdings = []
            facts: List[NumericFact] = []
            used_estimated_prices = False

            for item in holdings_raw:
                symbol = str(item.get("symbol", "")).strip().upper()
                if not symbol:
                    continue

                shares = Decimal(str(item.get("shares", 0)))
                avg_price = Decimal(str(item.get("avg_price", 0)))

                # Lookup security and latest price
                security = Security.objects.filter(symbol__iexact=symbol).select_related('company').first()
                company_name = security.company.legal_name if security else symbol
                sector = security.company.sector if security and security.company.sector else "Diversified"

                # Check latest close price observation
                latest_obs = None
                if security:
                    latest_obs = MarketObservation.objects.filter(
                        security=security, metric="close_price"
                    ).order_by('-observed_at').first()

                if latest_obs:
                    curr_price = latest_obs.value_decimal
                    price_basis = "Stored exchange close"
                    price_as_of = latest_obs.observed_at.strftime("%Y-%m-%d")
                elif item.get("current_price") is not None:
                    curr_price = Decimal(str(item["current_price"]))
                    price_basis = "User supplied price"
                    price_as_of = "User supplied; date unverified"
                    used_estimated_prices = True
                else:
                    curr_price = avg_price
                    price_basis = "Average purchase price proxy"
                    price_as_of = "Purchase price; not a current quote"
                    used_estimated_prices = True
                curr_value = (shares * curr_price).quantize(Decimal("0.01"))
                total_value += curr_value

                sector_totals[sector] = sector_totals.get(sector, Decimal(0)) + curr_value

                processed_holdings.append({
                    "symbol": symbol,
                    "company_name": company_name,
                    "shares": str(shares),
                    "avg_price": str(avg_price),
                    "current_price": str(curr_price),
                    "current_value": str(curr_value),
                    "sector": sector,
                    "price_as_of": price_as_of,
                    "valuation_basis": price_basis
                })

            if total_value <= 0:
                raise ValueError("Total portfolio value is zero or no valid holdings provided.")

            # Calculate sector concentrations deterministically
            sector_breakdown = []
            for sec_name, sec_val in sector_totals.items():
                pct = ((sec_val / total_value) * Decimal(100)).quantize(Decimal("0.01"))
                sector_breakdown.append(SectorConcentration(
                    sector=sec_name,
                    value=sec_val,
                    percentage=pct
                ))

            sector_breakdown.sort(key=lambda x: x.percentage, reverse=True)
            processed_holdings.sort(key=lambda x: Decimal(x["current_value"]), reverse=True)

            calc_lineage = [
                "Computed holding values as shares multiplied by the displayed valuation basis.",
                f"Total portfolio valuation: INR {total_value:,.2f}",
                f"Sector exposure % formula: (sector_value / total_portfolio_value) * 100",
                f"Identified {len(sector_breakdown)} distinct sector buckets."
            ]
            if used_estimated_prices:
                calc_lineage.append("One or more holdings use user-supplied or average purchase price proxies; the total is not a current market valuation.")

            result_obj = PortfolioAnalysisResult(
                total_portfolio_value=total_value,
                holdings_count=len(processed_holdings),
                sector_breakdown=sector_breakdown,
                top_holdings=processed_holdings[:5],
                calculation_lineage=calc_lineage
            )

            # Fact for total portfolio
            facts.append(NumericFact(
                fact_id=f"fact_port_val_{tool_run_id}",
                metric="Total Portfolio Value",
                value=total_value,
                display_value=f"INR {total_value:,.2f}",
                unit="INR",
                period_or_observation_date="Valuation date varies by holding; see displayed basis",
                source_name="FinSight Portfolio Engine",
                source_url_or_document_id=tool_run_id,
                source_locator="Portfolio Holdings Calculator",
                fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                freshness="historical",
                calculation={"formula": "sum(shares * price)", "tool_run_id": tool_run_id}
            ))

            duration_ms = (time.time() - start_time) * 1000

            return ToolResult(
                tool_name="portfolio_analyzer",
                tool_run_id=tool_run_id,
                status="success",
                duration_ms=duration_ms,
                data=result_obj.model_dump(),
                facts=facts,
                citations=[],
                source_attribution="FinSight Deterministic Portfolio Calculator (Holding Records + Exchange Bhavcopy)",
                as_of=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                freshness="historical"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="portfolio_analyzer",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=f"Portfolio calculation error: {str(e)}",
                source_attribution="Portfolio Calculator",
                freshness="current"
            )
