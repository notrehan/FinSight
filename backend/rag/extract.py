import sys
from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def extract_pdf(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append(
            f"\n--- PAGE {page_number} ---\n{text}"
        )

    return "\n".join(pages)


def main():
    if len(sys.argv) != 2:
        print("Usage: python backend/rag/extract.py <company>")
        return

    company = sys.argv[1].lower()

    source_dir = PROJECT_ROOT / "data" / "documents" / company
    output_dir = PROJECT_ROOT / "data" / "processed" / company

    if not source_dir.exists():
        print(f"No document folder found: {source_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(source_dir.glob("*.pdf"))

    print(f"Company: {company}")
    print(f"Found {len(pdf_files)} PDFs.")

    for pdf_path in pdf_files:
        print(f"Extracting: {pdf_path.name}")

        text = extract_pdf(pdf_path)

        output_path = output_dir / f"{pdf_path.stem}.txt"
        output_path.write_text(
            text,
            encoding="utf-8",
        )

        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()