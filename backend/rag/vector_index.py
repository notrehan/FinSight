"""Optional FAISS index for page-aware filing chunks.

Index metadata records the model and corpus fingerprint so an index can be
rebuilt and audited. Keyword retrieval remains available when optional native
dependencies or the embedding model are not installed.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from django.conf import settings
from apps.documents.models import DocumentChunk


class VectorIndex:
    @staticmethod
    def _dependencies():
        try:
            import faiss
            import numpy as np
            from sentence_transformers import SentenceTransformer
            return faiss, np, SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install backend/requirements-rag.txt to build or query the semantic index."
            ) from exc

    @staticmethod
    def _paths() -> tuple[Path, Path]:
        directory = Path(settings.VECTOR_INDEX_PATH)
        return directory / "filings.faiss", directory / "filings.metadata.json"

    @classmethod
    def build(cls, batch_size: int = 64) -> dict[str, Any]:
        faiss, np, SentenceTransformer = cls._dependencies()
        chunks = list(
            DocumentChunk.objects.select_related("document")
            .filter(document__status="active")
            .order_by("document_id", "chunk_index")
        )
        if not chunks:
            raise RuntimeError("No active document chunks are available to index.")
        model_name = settings.EMBEDDING_MODEL
        model = SentenceTransformer(model_name)
        texts = [chunk.text for chunk in chunks]
        vectors = model.encode(
            texts, batch_size=batch_size, convert_to_numpy=True,
            normalize_embeddings=True, show_progress_bar=False,
        ).astype("float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        index_path, metadata_path = cls._paths()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(index_path))
        corpus_digest = hashlib.sha256(
            "\n".join(f"{chunk.id}:{chunk.document.checksum}:{chunk.text}" for chunk in chunks).encode("utf-8")
        ).hexdigest()
        metadata = {
            "schema_version": 1,
            "embedding_model": model_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "corpus_sha256": corpus_digest,
            "dimension": int(vectors.shape[1]),
            "chunk_ids": [chunk.id for chunk in chunks],
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return {"chunk_count": len(chunks), "embedding_model": model_name, "corpus_sha256": corpus_digest}

    @classmethod
    def search(cls, query: str, company_id: Optional[int] = None,
               fiscal_period: Optional[str] = None, doc_type: Optional[str] = None,
               top_k: int = 4) -> Optional[list[dict[str, Any]]]:
        faiss, np, SentenceTransformer = cls._dependencies()
        index_path, metadata_path = cls._paths()
        if not index_path.is_file() or not metadata_path.is_file():
            return None
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("embedding_model") != settings.EMBEDDING_MODEL:
            return None
        model = SentenceTransformer(settings.EMBEDDING_MODEL)
        query_vector = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        index = faiss.read_index(str(index_path))
        scores, positions = index.search(query_vector, min(max(top_k * 25, 50), index.ntotal))
        ranked_ids = [metadata["chunk_ids"][int(position)] for position in positions[0] if position >= 0]
        qs = DocumentChunk.objects.select_related("document", "document__company").filter(id__in=ranked_ids)
        if company_id:
            qs = qs.filter(document__company_id=company_id)
        if fiscal_period:
            qs = qs.filter(document__fiscal_period__iexact=fiscal_period)
        if doc_type:
            qs = qs.filter(document__document_type=doc_type)
        chunks_by_id = {chunk.id: chunk for chunk in qs}
        score_by_id = {
            ranked_ids[index_position]: float(score)
            for index_position, score in enumerate(scores[0])
            if index_position < len(ranked_ids)
        }
        results = []
        for chunk_id in ranked_ids:
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
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
                "score": score_by_id.get(chunk_id, 0.0),
                "retrieval_mode": "faiss_sentence_transformers",
            })
            if len(results) >= top_k:
                break
        return results
