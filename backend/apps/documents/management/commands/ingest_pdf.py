from django.core.management.base import BaseCommand, CommandError
from rag.ingest import ingest_pdf


class Command(BaseCommand):
    help = "Ingest a public filing PDF into page-aware document chunks."

    def add_arguments(self, parser):
        parser.add_argument("pdf_path")
        parser.add_argument("--company-id", type=int, required=True)
        parser.add_argument("--title", required=True)
        parser.add_argument("--period", required=True)
        parser.add_argument("--source-url", required=True)
        parser.add_argument("--source-name", required=True)
        parser.add_argument("--license-terms", required=True, help="Reviewed license/terms or explicit public-source conditions.")
        parser.add_argument("--refresh-policy", default="manual")
        parser.add_argument("--document-type", default="annual_report", choices=["annual_report", "earnings_call", "presentation", "financial_results"])

    def handle(self, *args, **options):
        try:
            document = ingest_pdf(options["pdf_path"], options["company_id"], options["title"],
                                  options["period"], options["document_type"], options["source_url"],
                                  options["source_name"], options["license_terms"], options["refresh_policy"])
        except Exception as exc:
            if isinstance(exc, CommandError):
                raise
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Ingested document {document.id}: {document.chunks.count()} chunks ({document.checksum})"))
