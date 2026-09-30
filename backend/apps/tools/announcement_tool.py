"""
Announcement retrieval tool.
Fetches exchange announcements (BSE/NSE disclosures, corporate actions, board meetings)
with source attribution and published timestamps.
"""
import uuid
import time
from typing import Optional, List, Dict, Any
from schemas.contracts import ToolResult, Citation
from apps.observability.models import ToolRun
from apps.companies.models import Company, Security
from apps.announcements.models import Announcement

class AnnouncementRetrievalTool:
    @staticmethod
    def get_announcements(
        company_id_or_symbol: Any = None,
        category: Optional[str] = None,
        limit: int = 10,
        trace_id: str = ""
    ) -> ToolResult:
        start_time = time.time()
        tool_run_id = f"ann_{uuid.uuid4().hex[:8]}"
        citations: List[Citation] = []

        try:
            queryset = Announcement.objects.select_related('company').order_by('-published_at')

            company = None
            if company_id_or_symbol:
                if isinstance(company_id_or_symbol, int) or (isinstance(company_id_or_symbol, str) and str(company_id_or_symbol).isdigit()):
                    company = Company.objects.filter(id=int(company_id_or_symbol)).first()
                if not company and isinstance(company_id_or_symbol, str):
                    sec = Security.objects.filter(symbol__iexact=company_id_or_symbol).select_related('company').first()
                    if sec:
                        company = sec.company
                    else:
                        company = Company.objects.filter(legal_name__icontains=company_id_or_symbol).first()

            if company:
                queryset = queryset.filter(company=company)

            if category:
                queryset = queryset.filter(category__iexact=category)

            ann_list = list(queryset[:limit])
            records = []

            for ann in ann_list:
                citation = Citation(
                    document_id=f"ann_{ann.id}",
                    title=f"Exchange Disclosure: {ann.category} - {ann.headline[:60]}",
                    page=None,
                    section=ann.category,
                    source_url=ann.source_url
                )
                citations.append(citation)

                records.append({
                    "id": ann.id,
                    "company_name": ann.company.legal_name,
                    "category": ann.category,
                    "headline": ann.headline,
                    "body": ann.body,
                    "published_at": ann.published_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "source_url": ann.source_url
                })

            duration_ms = (time.time() - start_time) * 1000

            try:
                ToolRun.objects.create(
                    trace_id=trace_id,
                    tool_name="announcement_retrieval",
                    input_hash=str(company_id_or_symbol or "ALL"),
                    status="success",
                    duration_ms=duration_ms,
                    source_id="bse_nse_disclosures",
                    details={"count": len(records)}
                )
            except Exception:
                pass

            return ToolResult(
                tool_name="announcement_retrieval",
                tool_run_id=tool_run_id,
                status="success",
                duration_ms=duration_ms,
                data={
                    "announcements": records,
                    "count": len(records)
                },
                facts=[],
                citations=citations,
                source_attribution="BSE / NSE Corporate Announcements Feed",
                as_of=records[0]["published_at"] if records else "Latest Available",
                freshness="delayed"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name="announcement_retrieval",
                tool_run_id=tool_run_id,
                status="error",
                duration_ms=duration_ms,
                data=None,
                error_message=str(e),
                source_attribution="Corporate Disclosures",
                freshness="delayed"
            )
