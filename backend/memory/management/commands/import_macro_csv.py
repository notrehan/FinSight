import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from memory.models import MacroObservation


class Command(BaseCommand):
    help = "Import source-linked RBI DBIE macro observations from CSV."

    def add_arguments(self, parser):
        parser.add_argument("csv_file")

    def handle(self, *args, **options):
        count = 0
        try:
            with open(options["csv_file"], newline="", encoding="utf-8-sig") as source:
                for row in csv.DictReader(source):
                    series = (row.get("series") or "").strip()
                    period = (row.get("period") or "").strip()
                    unit = (row.get("unit") or "").strip()
                    source_url = (row.get("source_url") or "").strip()
                    if not all((series, period, unit)) or not source_url.startswith("https://"):
                        raise ValueError("Each row needs series, period, unit, and an HTTPS source_url")
                    observed_at = datetime.fromisoformat(row["observed_at"].strip().replace("Z", "+00:00"))
                    if observed_at.tzinfo is None:
                        raise ValueError("observed_at must include a timezone")
                    value = Decimal(row["value"].strip())
                    if not value.is_finite():
                        raise ValueError("value must be finite")
                    MacroObservation.objects.update_or_create(
                        series=series, period=period, source_url=source_url,
                        defaults={"value": value, "unit": unit, "observed_at": observed_at},
                    )
                    count += 1
        except (OSError, KeyError, ValueError, InvalidOperation, csv.Error) as exc:
            raise CommandError(f"Import failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Imported or updated {count} source-linked RBI observations."))
