import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer

from companies import COMPANIES


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_NAME = "all-MiniLM-L6-v2"

print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)


def search(company: str, query: str, top_k: int = 5):
    company = company.lower().strip()

    if company not in COMPANIES:
        raise ValueError(
            f"Unsupported company: {company}. "
            f"Supported companies: {', '.join(COMPANIES.keys())}"
        )

    vector_dir = (
        PROJECT_ROOT
        / "data"
        / "vectorstore"
        / company
    )

    index_path = vector_dir / "index.faiss"
    metadata_path = vector_dir / "metadata.json"

    if not index_path.exists():
        raise FileNotFoundError(
            f"No FAISS index found for {company}."
        )

    index = faiss.read_index(str(index_path))

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    )

    scores, indices = index.search(
        query_embedding,
        top_k,
    )

    results = []

    for score, index_id in zip(
        scores[0],
        indices[0],
    ):
        result = metadata[index_id].copy()

        result["score"] = float(score)
        result["company"] = company

        results.append(result)

    return results


if __name__ == "__main__":
    company = input(
        "Company (infosys/tcs): "
    ).strip()

    question = input(
        "Ask a question: "
    ).strip()

    try:
        results = search(
            company=company,
            query=question,
            top_k=5,
        )

        print("\nRelevant chunks:\n")

        for i, result in enumerate(
            results,
            start=1,
        ):
            print("=" * 80)
            print(f"Result {i}")
            print(f"Company: {result['company']}")
            print(f"Score: {result['score']:.4f}")
            print(f"Document: {result['document']}")
            print(f"Page: {result['page']}")
            print()
            print(result["text"][:1500])

    except Exception as error:
        print(f"\nError: {error}")