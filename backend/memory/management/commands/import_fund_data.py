import csv
import json
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from memory.models import FundFactsheet, FundNav

AMFI_NAV_URL = "https://www.amfiindia.com/net-asset-value/nav-download"


def parse_date(value):
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported NAV date: {value}")


class Command(BaseCommand):
    help = "Import allowed AMFI NAV text or source-linked mutual-fund factsheet CSV records."

    def add_arguments(self, parser):
        parser.add_argument("kind", choices=("amfi-nav", "factsheets"))
        parser.add_argument("file")
        parser.add_argument("--confirm-terms", action="store_true", help="Confirm source terms permit your intended storage and display.")
        parser.add_argument("--source-url", default="")

    def handle(self, *args, **options):
        if not options["confirm_terms"]:
            raise CommandError("Review the source terms and confirm your intended use with --confirm-terms. This flag is not a license.")
        try:
            count = self.import_nav(options["file"]) if options["kind"] == "amfi-nav" else self.import_factsheets(options["file"], options["source_url"])
        except (OSError, UnicodeError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise CommandError(f"Import failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Imported or updated {count} {options['kind']} records."))

    def import_nav(self, path):
        count = 0
        with open(path, encoding="utf-8-sig") as source:
            for line in source:
                fields = [item.strip() for item in line.strip().split(";")]
                if len(fields) < 6 or not fields[0].isdigit():
                    continue
                # Current AMFI complete file has 8 columns; legacy NAVAll has 6.
                if len(fields) >= 8:
                    code, name, nav_text, date_text = fields[0], fields[3], fields[6], fields[7]
                else:
                    code, name, nav_text, date_text = fields[0], fields[3], fields[4], fields[5]
                if not name or not nav_text or nav_text.upper() in {"N.A.", "NA"}:
                    continue
                value = Decimal(nav_text)
                if not value.is_finite() or value < 0:
                    raise ValueError(f"Invalid NAV value for scheme {code}")
                nav_date = parse_date(date_text)
                FundNav.objects.update_or_create(scheme_code=code, date=nav_date,
                    defaults={"nav": value, "source_url": AMFI_NAV_URL})
                FundFactsheet.objects.update_or_create(scheme_code=code,
                    defaults={"scheme_name": name, "source_url": AMFI_NAV_URL,
                             "category": "", "expense_ratio": None, "holdings": {},
                             "latest_nav": value, "nav_date": nav_date})
                count += 1
        return count

    def import_factsheets(self, path, source_url):
        count = 0
        with open(path, newline="", encoding="utf-8-sig") as source:
            for row in csv.DictReader(source):
                row = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
                url = row.get("source_url") or source_url
                if not url.startswith("https://"):
                    raise ValueError("Each factsheet needs a source URL using HTTPS")
                code, name = row["scheme_code"], row["scheme_name"]
                ratio = Decimal(row["expense_ratio"]) if row.get("expense_ratio") else None
                if ratio is not None and (not ratio.is_finite() or not 0 <= ratio <= 100):
                    raise ValueError("expense_ratio must be a finite percentage from 0 to 100")
                holdings = json.loads(row.get("holdings_json") or "{}")
                if not isinstance(holdings, dict):
                    raise ValueError("holdings_json must be a JSON object")
                clean = {}
                for ticker, weight in holdings.items():
                    value = Decimal(str(weight))
                    if not value.is_finite() or not 0 <= value <= 100:
                        raise ValueError("holding weights must be percentages from 0 to 100")
                    clean[str(ticker).strip().upper()] = float(value)
                FundFactsheet.objects.update_or_create(scheme_code=code, defaults={
                    "scheme_name": name, "category": row.get("category", ""),
                    "expense_ratio": ratio, "holdings": clean, "source_url": url,
                })
                count += 1
        return count
