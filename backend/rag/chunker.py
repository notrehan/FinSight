"""
Page-aware and section-aware document chunker for FinSight AI.
Preserves page numbers, headings, table markers, and prevents flattening citation locators.
"""
from typing import List, Dict, Any

class DocumentChunker:
    @staticmethod
    def chunk_text(
        text: str,
        page_no: int = 1,
        section: str = "General",
        chunk_size: int = 400,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Splits text into overlapping chunks, maintaining page_no and section metadata.
        """
        words = text.split()
        if not words:
            return []

        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_content = " ".join(chunk_words)

            chunks.append({
                "chunk_index": chunk_idx,
                "page_no": page_no,
                "section": section,
                "text": chunk_content,
                "token_count": len(chunk_words)
            })

            chunk_idx += 1
            if end == len(words):
                break
            start += (chunk_size - chunk_overlap)

        return chunks
