"""
Deterministic financial calculator tool.
Enforces the core rule: LLM performs zero arithmetic; all calculations are executed deterministically
with full operand lineage, Decimal precision, and strict boundary checks (e.g. division by zero).
"""
import uuid
import time
from decimal import Decimal, InvalidOperation, DivisionByZero
from typing import Dict, Any, List, Optional
from schemas.contracts import ToolResult, NumericFact
from apps.observability.models import ToolRun

class FinancialCalculator:
    """
    Allowlisted formulas:
    - revenue_growth_pct: ((current - prior) / prior) * 100
    - profit_margin_pct: (profit / revenue) * 100
    - debt_to_equity: debt / equity
    - market_cap: price * shares
    - sector_exposure_pct: (sector_value / total_value) * 100
    - pe_ratio: price / eps
    - general_division: a / b
    - percentage_change: ((new - old) / old) * 100
    """

    @staticmethod
    def calculate(
        formula: str,
        operands: Dict[str, Any],
        units: Dict[str, str],
        trace_id: str = "",
        operand_facts: Optional[List[NumericFact]] = None
    ) -> ToolResult:
        start_time = time.time()
        tool_run_id = f"calc_{uuid.uuid4().hex[:8]}"
        operand_facts = operand_facts or []
        facts: List[NumericFact] = []
        errors = []

        try:
            # Convert all operands to Decimal
            dec_operands = {}
            for k, v in operands.items():
                try:
                    dec_operands[k] = Decimal(str(v))
                except (InvalidOperation, ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value for operand '{k}': {v}")

            result_value: Optional[Decimal] = None
            display_value = ""
            result_unit = "%"
            metric_name = formula

            if formula in ("revenue_growth_pct", "percentage_change"):
                current = dec_operands.get("current") if "current" in dec_operands else dec_operands.get("new")
                prior = dec_operands.get("prior") if "prior" in dec_operands else dec_operands.get("old")
                if current is None or prior is None:
                    raise ValueError("Requires 'current' and 'prior' (or 'new' and 'old') operands.")
                if prior == 0:
                    raise DivisionByZero("Prior period value is 0; growth percentage is undefined.")
                
                # Formula: ((current - prior) / abs(prior)) * 100
                diff = current - prior
                result_value = (diff / abs(prior)) * Decimal(100)
                result_value = result_value.quantize(Decimal("0.01"))
                display_value = f"{result_value:+0.2f}%"
                result_unit = "%"
                metric_name = "Revenue Growth"

            elif formula == "profit_margin_pct":
                profit = dec_operands.get("profit")
                revenue = dec_operands.get("revenue")
                if profit is None or revenue is None:
                    raise ValueError("Requires 'profit' and 'revenue' operands.")
                if revenue <= 0:
                    raise DivisionByZero("Revenue is zero or negative; profit margin is undefined.")
                result_value = (profit / revenue) * Decimal(100)
                result_value = result_value.quantize(Decimal("0.01"))
                display_value = f"{result_value:0.2f}%"
                result_unit = "%"
                metric_name = "Profit Margin"

            elif formula == "debt_to_equity":
                debt = dec_operands.get("debt") or dec_operands.get("total_debt")
                equity = dec_operands.get("equity") or dec_operands.get("total_equity")
                if debt is None or equity is None:
                    raise ValueError("Requires 'debt' and 'equity' operands.")
                if equity <= 0:
                    raise DivisionByZero("Shareholder equity is zero or negative; Debt-to-Equity ratio cannot be computed safely.")
                result_value = (debt / equity).quantize(Decimal("0.001"))
                display_value = f"{result_value:0.2f}x"
                result_unit = "ratio"
                metric_name = "Debt-to-Equity"

            elif formula == "market_cap":
                price = dec_operands.get("price")
                shares = dec_operands.get("shares")
                if price is None or shares is None:
                    raise ValueError("Requires 'price' and 'shares' operands.")
                result_value = (price * shares).quantize(Decimal("0.01"))
                display_value = f"INR {result_value:,.2f}"
                result_unit = units.get("result", "INR")
                metric_name = "Market Capitalization"

            elif formula == "pe_ratio":
                price = dec_operands.get("price")
                eps = dec_operands.get("eps")
                if price is None or eps is None:
                    raise ValueError("Requires 'price' and 'eps' operands.")
                if eps <= 0:
                    raise DivisionByZero("EPS is zero or negative; P/E ratio is not meaningful.")
                result_value = (price / eps).quantize(Decimal("0.01"))
                display_value = f"{result_value:0.2f}x"
                result_unit = "ratio"
                metric_name = "P/E Ratio"

            elif formula == "sector_exposure_pct":
                sector_val = dec_operands.get("sector_value")
                total_val = dec_operands.get("total_value")
                if sector_val is None or total_val is None:
                    raise ValueError("Requires 'sector_value' and 'total_value' operands.")
                if total_val <= 0:
                    raise DivisionByZero("Total portfolio value is zero or negative.")
                result_value = (sector_val / total_val) * Decimal(100)
                result_value = result_value.quantize(Decimal("0.01"))
                display_value = f"{result_value:0.2f}%"
                result_unit = "%"
                metric_name = "Sector Exposure"

            else:
                raise ValueError(f"Unsupported formula: '{formula}'. Only allowlisted deterministic formulas allowed.")

            # Create provenanced fact
            operand_ids = [f.fact_id for f in operand_facts if hasattr(f, 'fact_id')]
            calc_fact = NumericFact(
                fact_id=f"fact_calc_{tool_run_id}",
                metric=metric_name,
                value=result_value,
                display_value=display_value,
                unit=result_unit,
                period_or_observation_date="Calculated",
                source_name="FinSight Deterministic Calculator",
                source_url_or_document_id=tool_run_id,
                source_locator=f"formula: {formula}",
                fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                freshness="current",
                calculation={
                    "formula": formula,
                    "operands": {k: str(v) for k, v in operands.items()},
                    "operand_fact_ids": operand_ids,
                    "tool_run_id": tool_run_id
                }
            )
            facts.append(calc_fact)

            duration_ms = (time.time() - start_time) * 1000

            # Audit record in DB if available
            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="calculator",
                    input_hash=formula,
                    status="success",
                    duration_ms=duration_ms,
                    source_id="internal_calculator",
                    details={"formula": formula, "operands": {k: str(v) for k, v in operands.items()}, "result": str(result_value)}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="calculator",
                tool_run_id=tool_run_id,
                status="success",
                duration_ms=duration_ms,
                data={
                    "formula": formula,
                    "operands": {k: str(v) for k, v in operands.items()},
                    "result_value": str(result_value),
                    "display_value": display_value,
                    "unit": result_unit
                },
                facts=facts,
                citations=[],
                source_attribution="FinSight Deterministic Financial Calculator (Exact Arithmetic)",
                as_of=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                freshness="current"
            )

        except (DivisionByZero, ZeroDivisionError) as zde:
            duration_ms = (time.time() - start_time) * 1000
            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="calculator",
                    input_hash=formula,
                    status="error",
                    duration_ms=duration_ms,
                    error_code="DIVISION_BY_ZERO",
                    details={"formula": formula, "error": str(zde)}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="calculator",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=f"Cannot calculate from supplied inputs: {str(zde)}",
                source_attribution="FinSight Calculator",
                freshness="current"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="calculator",
                    input_hash=formula,
                    status="error",
                    duration_ms=duration_ms,
                    error_code="CALC_ERROR",
                    details={"formula": formula, "error": str(e)}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="calculator",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=f"Calculator error: {str(e)}",
                source_attribution="FinSight Calculator",
                freshness="current"
            )
