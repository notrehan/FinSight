from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "data" / "documents" / "infosys"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "infosys"


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(SOURCE_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    print(f"Found {len(pdf_files)} PDFs.")

    for pdf_path in pdf_files:
        print(f"Extracting: {pdf_path.name}")

        text = extract_pdf(pdf_path)

        output_path = OUTPUT_DIR / f"{pdf_path.stem}.txt"
        output_path.write_text(text, encoding="utf-8")

        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()