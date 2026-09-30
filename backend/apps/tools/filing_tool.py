"""
Filing retrieval tool.
Extracts grounded evidence passages from company filings (Annual Reports, Earnings Calls, Transcripts)
with precise page numbers, section titles, and source URLs.
"""
import uuid
import time
from typing import Optional, List, Dict, Any
from schemas.contracts import ToolResult, Citation
from apps.observability.models import ToolRun
from apps.companies.models import Company, Security
from apps.documents.models import Document, DocumentChunk
from rag.retriever import RAGRetriever

class FilingRetrievalTool:
    @staticmethod
    def retrieve(
        company_id_or_symbol: Any,
        query: str,
        period: Optional[str] = None,
        doc_type: Optional[str] = None,
        top_k: int = 4,
        trace_id: str = ""
    ) -> ToolResult:
        start_time = time.time()
        tool_run_id = f"rag_{uuid.uuid4().hex[:8]}"
        citations: List[Citation] = []

        try:
            # Resolve company
            company = None
            if isinstance(company_id_or_symbol, int) or (isinstance(company_id_or_symbol, str) and str(company_id_or_symbol).isdigit()):
                company = Company.objects.filter(id=int(company_id_or_symbol)).first()
            if not company and isinstance(company_id_or_symbol, str):
                sec = Security.objects.filter(symbol__iexact=company_id_or_symbol).select_related('company').first()
                if sec:
                    company = sec.company
                else:
                    company = Company.objects.filter(legal_name__icontains=company_id_or_symbol).first()

            passages = RAGRetriever.search(
                query=query,
                company_id=company.id if company else None,
                fiscal_period=period,
                doc_type=doc_type,
                top_k=max(1, min(top_k, 20)),
            )

            for passage in passages:
                citation = Citation(
                    document_id=f"doc_{passage['document_id']}",
                    title=f"{passage['document_title']} ({passage['fiscal_period']})",
                    page=passage["page_no"],
                    section=passage["section"] or "Report Section",
                    source_url=passage["source_url"]
                )
                citations.append(citation)

            duration_ms = (time.time() - start_time) * 1000

            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="filing_retrieval",
                    input_hash=query[:64],
                    status="success",
                    duration_ms=duration_ms,
                    source_id="document_chunks",
                    details={"company": company.legal_name if company else "All", "matches": len(passages)}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="filing_retrieval",
                tool_run_id=tool_run_id,
                status="success",
                duration_ms=duration_ms,
                data={
                    "query": query,
                    "matched_count": len(passages),
                    "passages": passages,
                    "retrieval_mode": passages[0].get("retrieval_mode", "keyword_fallback") if passages else "no_match",
                },
                facts=[],
                citations=citations,
                source_attribution="Official Company Filings and Transcripts (BSE/NSE/SEBI)",
                as_of=period or "Latest Published",
                freshness="historical"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="filing_retrieval",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=str(e),
                source_attribution="Company Filings",
                freshness="historical"
            )
