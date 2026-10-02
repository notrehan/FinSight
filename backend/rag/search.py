import json
from functools import lru_cache
from pathlib import Path
import re

from .companies import COMPANIES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_NAME = "all-MiniLM-L6-v2"
MULTILINGUAL_MODEL = "intfloat/multilingual-e5-base"


@lru_cache(maxsize=2)
def _embedding_model(model_name):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def search(company: str, query: str, top_k: int = 5):
    company = company.lower().strip()
    if company not in COMPANIES:
        raise ValueError(f"Unsupported company: {company}. Supported companies: {', '.join(COMPANIES)}")
    vector_dir = PROJECT_ROOT / "data" / "vectorstore" / company
    index_path, metadata_path = vector_dir / "index.faiss", vector_dir / "metadata.json"
    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(f"No indexed filings found for {company}.")
    import faiss
    index = faiss.read_index(str(index_path))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    # For an explicitly requested quarter, do not let a semantically similar
    # passage from a different year masquerade as evidence for that period.
    allowed_ids = None
    quarter_match = re.search(
        r"\bq(?:uarter)?\s*([1-4])\s*(?:of\s*)?(?:fy\s*)?(20\d{2}|\d{2})\b",
        query,
        re.IGNORECASE,
    )
    if quarter_match:
        quarter, year = quarter_match.groups()
        full_year = year if len(year) == 4 else f"20{year}"
        short_year = full_year[-2:]
        period_patterns = (
            re.compile(rf"\bq{quarter}\s*(?:fy\s*)?{full_year}\b", re.IGNORECASE),
            re.compile(rf"\bq{quarter}\s*(?:fy\s*)?{short_year}\b", re.IGNORECASE),
            re.compile(rf"\bquarter\s*{quarter}\s*(?:fy\s*)?{full_year}\b", re.IGNORECASE),
        )
        allowed_ids = {
            i for i, item in enumerate(metadata)
            if any(pattern.search(str(item.get("text", ""))) for pattern in period_patterns)
            or any(pattern.search(str(item.get("document", ""))) for pattern in period_patterns)
        }
        if not allowed_ids:
            return []

    config_path = vector_dir / "index_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        model_name = config.get("embedding_model", MULTILINGUAL_MODEL)
    else:
        model_name = MODEL_NAME
    query_terms = query
    lowered_query = query.casefold()
    if re.search(r"\b(profit|earnings|pat)\b", lowered_query):
        query_terms += " net profit net income profit after tax PAT"
    if re.search(r"\b(revenue|sales|turnover)\b", lowered_query):
        query_terms += " revenue from operations sales turnover"
    if re.search(r"\b(expense|cost)\b", lowered_query):
        query_terms += " expenses costs operating expenses"
    prefix = "query: " if "e5" in model_name.casefold() else ""
    embedding = _embedding_model(model_name).encode([prefix + query_terms], normalize_embeddings=True)
    # The FAISS index is built against the full metadata array. If an exact
    # period filter was applied, rank only those eligible chunks by cosine
    # similarity so other periods cannot leak back into the result.
    if allowed_ids is not None:
        scores_all, indices_all = index.search(embedding, index.ntotal)
        ranked = [(score, idx) for score, idx in zip(scores_all[0], indices_all[0]) if int(idx) in allowed_ids]
        ranked = ranked[: min(max(1, top_k), len(ranked))]
        scores, indices = [[score for score, _ in ranked]], [[idx for _, idx in ranked]]
    else:
        scores, indices = index.search(embedding, min(max(1, top_k), len(metadata)))
    results = []
    for score, index_id in zip(scores[0], indices[0]):
        if 0 <= index_id < len(metadata):
            item = metadata[index_id].copy()
            item.update({"score": float(score), "company": company})
            results.append(item)
    return results
