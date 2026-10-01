import json
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_NAME = "all-MiniLM-L6-v2"


def get_company_paths(company: str):
    chunks_dir = PROJECT_ROOT / "data" / "chunks" / company
    vector_dir = PROJECT_ROOT / "data" / "vectorstore" / company

    return chunks_dir, vector_dir


def load_chunks(chunks_dir):
    records = []

    for file_path in sorted(chunks_dir.glob("*.json")):
        chunks = json.loads(
            file_path.read_text(encoding="utf-8")
        )

        records.extend(chunks)

    return records


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("python backend/rag/embed_and_index.py <company>")
        return

    company = sys.argv[1].lower()

    chunks_dir, vector_dir = get_company_paths(company)

    if not chunks_dir.exists():
        print(f"No chunks found for company: {company}")
        return

    vector_dir.mkdir(parents=True, exist_ok=True)

    print(f"Indexing company: {company}")

    records = load_chunks(chunks_dir)

    print(f"Loaded {len(records)} chunks.")

    texts = [record["text"] for record in records]

    print("Loading embedding model...")

    model = SentenceTransformer(MODEL_NAME)

    print("Creating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32",
    )

    index = faiss.IndexFlatIP(
        embeddings.shape[1]
    )

    index.add(embeddings)

    index_path = vector_dir / "index.faiss"
    metadata_path = vector_dir / "metadata.json"

    faiss.write_index(
        index,
        str(index_path),
    )

    metadata_path.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("Done.")
    print(f"Company: {company}")
    print(f"Vectors stored: {index.ntotal}")


if __name__ == "__main__":
    main()