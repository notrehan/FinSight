"""
Registry and router for FinSight deterministic tools.
"""
from typing import Dict, Any, Optional
from schemas.contracts import ToolResult
from .price_tool import PriceLookupTool
from .fundamentals_tool import FundamentalsLookupTool
from .calculator_tool import FinancialCalculator
from .filing_tool import FilingRetrievalTool
from .announcement_tool import AnnouncementRetrievalTool
from .portfolio_tool import PortfolioAnalyzerTool

class ToolRegistry:
    @staticmethod
    def execute_tool(tool_name: str, arguments: Dict[str, Any], trace_id: str = "") -> ToolResult:
        if tool_name == "price_lookup":
            return PriceLookupTool.get_prices(
                symbol_or_id=arguments.get("symbol") or arguments.get("company_id") or arguments.get("security_id"),
                exchange=arguments.get("exchange"),
                days=int(arguments.get("days", 5)),
                trace_id=trace_id
            )
        elif tool_name == "fundamentals_lookup":
            return FundamentalsLookupTool.get_fundamentals(
                company_id_or_symbol=arguments.get("company_id") or arguments.get("symbol"),
                metric=arguments.get("metric"),
                period=arguments.get("period"),
                trace_id=trace_id
            )
        elif tool_name == "calculator":
            return FinancialCalculator.calculate(
                formula=arguments.get("formula", ""),
                operands=arguments.get("operands", {}),
                units=arguments.get("units", {}),
                trace_id=trace_id,
                operand_facts=arguments.get("operand_facts", [])
            )
        elif tool_name == "filing_retrieval":
            return FilingRetrievalTool.retrieve(
                company_id_or_symbol=arguments.get("company_id") or arguments.get("symbol"),
                query=arguments.get("query", ""),
                period=arguments.get("period"),
                doc_type=arguments.get("doc_type"),
                top_k=int(arguments.get("top_k", 4)),
                trace_id=trace_id
            )
        elif tool_name == "announcement_retrieval":
            return AnnouncementRetrievalTool.get_announcements(
                company_id_or_symbol=arguments.get("company_id") or arguments.get("symbol"),
                category=arguments.get("category"),
                limit=int(arguments.get("limit", 10)),
                trace_id=trace_id
            )
        elif tool_name == "portfolio_analyzer":
            return PortfolioAnalyzerTool.analyze_holdings(
                holdings_raw=arguments.get("holdings", []),
                trace_id=trace_id
            )
        else:
            raise ValueError(f"Unknown tool: '{tool_name}'")
