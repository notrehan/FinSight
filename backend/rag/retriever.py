"""
Semantic and metadata-filtered retriever for FinSight AI RAG.
Resolves document passages with exact page/section locators and source URLs.
"""
from typing import List, Optional, Any, Dict
from apps.documents.models import DocumentChunk, Document
from schemas.contracts import Citation

class RAGRetriever:
    @staticmethod
    def search(
        query: str,
        company_id: Optional[int] = None,
        fiscal_period: Optional[str] = None,
        doc_type: Optional[str] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Retrieves matching chunks with citations.
        """
        try:
            from .vector_index import VectorIndex
            vector_results = VectorIndex.search(query, company_id, fiscal_period, doc_type, top_k)
            if vector_results is not None:
                return vector_results
        except (RuntimeError, OSError, ValueError, KeyError):
            # Keep the lexical retriever available as a degraded mode. Tool
            # output records which retrieval mode produced the passages.
            pass

        qs = DocumentChunk.objects.select_related('document', 'document__company')
        if company_id:
            qs = qs.filter(document__company_id=company_id)
        if fiscal_period:
            qs = qs.filter(document__fiscal_period__iexact=fiscal_period)
        if doc_type:
            qs = qs.filter(document__document_type=doc_type)

        query_terms = [t.lower().strip(".,!?;:()[]{}\"'") for t in query.split() if len(t.strip(".,!?;:()[]{}\"'")) > 2]
        scored = []

        for chunk in qs.order_by("document__published_at", "document_id", "chunk_index")[:200]:
            text_lower = chunk.text.lower()
            section_lower = (chunk.section or '').lower()
            
            score = 0.0
            for term in query_terms:
                if term in text_lower:
                    score += 2.0
                if term in section_lower:
                    score += 3.0
            
            if score > 0 or not query_terms:
                scored.append((score, chunk))

        scored.sort(key=lambda x: (-x[0], -x[1].document.published_at.timestamp(), x[1].chunk_index))
        results = []

        for score, chunk in scored[:top_k]:
            doc = chunk.document
            results.append({
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "document_title": doc.title,
                "fiscal_period": doc.fiscal_period,
                "page_no": chunk.page_no,
                "section": chunk.section,
                "text": chunk.text,
                "source_url": doc.source_url,
                "score": score,
                "retrieval_mode": "keyword_fallback",
            })

        return results
