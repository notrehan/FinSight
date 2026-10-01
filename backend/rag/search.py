import json
from functools import lru_cache
from pathlib import Path

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
    config_path = vector_dir / "index_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        model_name = config.get("embedding_model", MULTILINGUAL_MODEL)
    else:
        model_name = MODEL_NAME
    prefix = "query: " if "e5" in model_name.casefold() else ""
    embedding = _embedding_model(model_name).encode([prefix + query], normalize_embeddings=True)
    scores, indices = index.search(embedding, min(max(1, top_k), len(metadata)))
    results = []
    for score, index_id in zip(scores[0], indices[0]):
        if 0 <= index_id < len(metadata):
            item = metadata[index_id].copy()
            item.update({"score": float(score), "company": company})
            results.append(item)
    return results
