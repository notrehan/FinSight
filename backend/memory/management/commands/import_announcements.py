import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from memory.models import Announcement


def classify(headline):
    value = headline.casefold()
    if any(word in value for word in ("result", "earnings", "audited", "unaudited")):
        return "results"
    if any(word in value for word in ("director", "resignation", "appointment", "board meeting")):
        return "board_changes"
    if any(word in value for word in ("pledge", "encumbrance")):
        return "pledges"
    if any(word in value for word in ("fundraise", "fund raising", "qip", "preferential", "debt issue")):
        return "fundraises"
    return "other"


class Command(BaseCommand):
    help = "Import exchange announcement CSV records as pending for human review."

    def add_arguments(self, parser):
        parser.add_argument("csv_file")
        parser.add_argument("--confirm-terms", action="store_true", help="Confirm the source permits the intended storage/display; this is not a license.")

    def handle(self, *args, **options):
        if not options["confirm_terms"]:
            raise CommandError("Review your source terms and pass --confirm-terms after confirming permitted use.")
        count = 0
        try:
            with open(options["csv_file"], newline="", encoding="utf-8-sig") as source:
                for row in csv.DictReader(source):
                    row = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
                    ticker, headline, source_url = row["ticker"].upper(), row["headline"], row["source_url"]
                    if not source_url.startswith("https://"):
                        raise ValueError("source_url must use HTTPS")
                    published_at = datetime.fromisoformat(row["published_at"].replace("Z", "+00:00"))
                    if published_at.tzinfo is None:
                        raise ValueError("published_at must have a timezone")
                    category = row.get("category") or classify(headline)
                    if category not in {"results", "board_changes", "pledges", "fundraises", "other"}:
                        category = classify(headline)
                    external_id = row.get("external_id") or f"{row.get('source','exchange')}:{ticker}:{published_at.isoformat()}:{headline[:60]}"
                    Announcement.objects.update_or_create(external_id=external_id, defaults={
                        "ticker": ticker, "headline": headline, "category": category,
                        "summary": row.get("summary", ""), "source": row.get("source", "Exchange"),
                        "source_url": source_url, "published_at": published_at,
                        "approval_status": "pending",
                    })
                    count += 1
        except (OSError, KeyError, ValueError, csv.Error) as exc:
            raise CommandError(f"Import failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Imported {count} items. All are pending human review and hidden from users."))
