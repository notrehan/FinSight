import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks" / "infosys"
VECTOR_DIR = PROJECT_ROOT / "data" / "vectorstore" / "infosys"

MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks():
    records = []

    for file_path in sorted(CHUNKS_DIR.glob("*.json")):
        chunks = json.loads(file_path.read_text(encoding="utf-8"))

        for chunk in chunks:
            records.append(chunk)

    return records


def main():
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading chunks...")
    records = load_chunks()

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

    embeddings = np.asarray(embeddings, dtype="float32")

    print(f"Embedding shape: {embeddings.shape}")

    # Because embeddings are normalized,
    # inner product is equivalent to cosine similarity.
    index = faiss.IndexFlatIP(embeddings.shape[1])

    index.add(embeddings)

    index_path = VECTOR_DIR / "index.faiss"
    metadata_path = VECTOR_DIR / "metadata.json"

    faiss.write_index(index, str(index_path))

    metadata_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nDone.")
    print(f"FAISS index: {index_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Vectors stored: {index.ntotal}")


if __name__ == "__main__":
    main()