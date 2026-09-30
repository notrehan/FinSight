from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "data" / "processed" / "infosys"
OUTPUT_DIR = PROJECT_ROOT / "data" / "chunks" / "infosys"

CHUNK_SIZE = 5000
OVERLAP = 500


def split_page_text(text: str) -> list[str]:
    """
    Split extracted page text into chunks while keeping overlap.
    """

    if len(text) <= CHUNK_SIZE:
        return [text.strip()]

    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += CHUNK_SIZE - OVERLAP

    return chunks


def process_document(file_path: Path):
    text = file_path.read_text(encoding="utf-8")

    chunks = []

    # Split on our page markers
    page_blocks = text.split("--- PAGE ")

    for page_block in page_blocks:
        if not page_block.strip():
            continue

        lines = page_block.split("\n", 1)

        # Example first line: "1 ---"
        page_number = lines[0].replace("---", "").strip()

        if not page_number.isdigit():
            continue

        page_number = int(page_number)

        page_text = lines[1].strip() if len(lines) > 1 else ""

        if not page_text:
            continue

        page_chunks = split_page_text(page_text)

        for chunk in page_chunks:
            chunks.append(
                {
                    "document": file_path.stem,
                    "page": page_number,
                    "text": chunk,
                }
            )

    return chunks


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    text_files = sorted(INPUT_DIR.glob("*.txt"))

    print(f"Found {len(text_files)} extracted documents.")

    total_chunks = 0

    for file_path in text_files:
        chunks = process_document(file_path)

        output_file = OUTPUT_DIR / f"{file_path.stem}.json"

        import json

        output_file.write_text(
            json.dumps(chunks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        total_chunks += len(chunks)

        print(
            f"{file_path.name}: {len(chunks)} chunks"
        )

    print(f"\nTotal chunks: {total_chunks}")


if __name__ == "__main__":
    main()