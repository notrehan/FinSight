"""Reproducible, page-aware PDF ingestion for the curated public filing corpus."""
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from django.core.management.base import CommandError
from pypdf import PdfReader

from apps.companies.models import Company
from apps.documents.models import Document, DocumentChunk
from .chunker import DocumentChunker


def ingest_pdf(pdf_path: str, company_id: int, title: str, fiscal_period: str,
               document_type: str = "annual_report", source_url: Optional[str] = None,
               source_name: Optional[str] = None, license_terms: Optional[str] = None,
               refresh_policy: str = "manual",
               chunk_size: int = 400, chunk_overlap: int = 50) -> Document:
    """Store a public PDF and page-located chunks. Repeated imports are idempotent."""
    path = Path(pdf_path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise CommandError("Input must be an existing PDF file.")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise CommandError("PDF exceeds the 50 MiB ingestion limit.")
    if not title.strip() or not fiscal_period.strip():
        raise CommandError("Title and fiscal period are required.")
    if not source_url or not source_url.startswith(("https://", "http://")):
        raise CommandError("Provide the canonical public source URL for this document.")
    if not source_name or not source_name.strip() or not license_terms or not license_terms.strip():
        raise CommandError("Provide the source name and reviewed license/terms before ingestion.")
    company = Company.objects.filter(pk=company_id).first()
    if company is None:
        raise CommandError(f"Company {company_id} does not exist.")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise CommandError("Encrypted PDFs cannot be ingested.")
    from apps.market_data.models import DataSource
    source, _ = DataSource.objects.update_or_create(
        source_name=source_name.strip(),
        defaults={
            "source_url": source_url,
            "license_terms": license_terms.strip(),
            "attribution_text": source_name.strip(),
            "refresh_policy": refresh_policy,
        },
    )
    document, _ = Document.objects.update_or_create(
        company=company, checksum=checksum,
        defaults={
            "document_type": document_type,
            "fiscal_period": fiscal_period.strip().upper(),
            "title": title.strip(),
            "source": source,
            "source_url": source_url,
            "published_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
            "status": "active",
        },
    )
    document.chunks.all().delete()
    chunk_index = 0
    for page_number, page in enumerate(reader.pages, start=1):
        for chunk in DocumentChunker.chunk_text(page.extract_text() or "", page_no=page_number,
                                               section="Extracted PDF page", chunk_size=400, chunk_overlap=50):
            DocumentChunk.objects.create(
                document=document, chunk_index=chunk_index, page_no=page_number,
                section=chunk["section"], text=chunk["text"], token_count=chunk["token_count"],
            )
            chunk_index += 1
    if chunk_index == 0:
        document.status = "unavailable_text"
        document.save(update_fields=["status"])
        raise CommandError("No extractable text found; OCR is required for this PDF.")
    return document
