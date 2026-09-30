import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VECTOR_DIR = PROJECT_ROOT / "data" / "vectorstore" / "infosys"

INDEX_PATH = VECTOR_DIR / "index.faiss"
METADATA_PATH = VECTOR_DIR / "metadata.json"

MODEL_NAME = "all-MiniLM-L6-v2"


def search(query: str, top_k: int = 5):
    index = faiss.read_index(str(INDEX_PATH))

    metadata = json.loads(
        METADATA_PATH.read_text(encoding="utf-8")
    )

    model = SentenceTransformer(MODEL_NAME)

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    )

    scores, indices = index.search(
        query_embedding,
        top_k,
    )

    results = []

    for score, index_id in zip(scores[0], indices[0]):
        result = metadata[index_id].copy()
        result["score"] = float(score)

        results.append(result)

    return results


if __name__ == "__main__":
    query = input("Ask a question: ")

    results = search(query)

    print("\nRelevant chunks:\n")

    for i, result in enumerate(results, start=1):
        print("=" * 80)
        print(f"Result {i}")
        print(f"Score: {result['score']:.4f}")
        print(f"Document: {result['document']}")
        print(f"Page: {result['page']}")
        print()
        print(result["text"][:1500])
        print()