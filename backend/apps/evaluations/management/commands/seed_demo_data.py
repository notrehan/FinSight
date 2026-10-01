from datetime import datetime, timezone, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from apps.announcements.models import Announcement
from apps.companies.models import Company, Security
from apps.documents.models import Document, DocumentChunk
from apps.market_data.models import DataSource, MarketObservation


class Command(BaseCommand):
    help = "Create/update the explicitly synthetic FinSight evaluation company and source data."

    def handle(self, *args, **options):
        company, _ = Company.objects.update_or_create(
            normalized_name="finsight evaluation demo company",
            defaults={
                "legal_name": "FinSight Evaluation Demo Company Ltd",
                "sector": "Synthetic Manufacturing",
                "industry": "Evaluation Fixture",
                "identifiers_json": {"synthetic": True},
                "description": "Synthetic records for software evaluation only; not a real issuer.",
            },
        )
        security, _ = Security.objects.update_or_create(
            exchange="TEST", symbol="FINSIGHTDEMO",
            defaults={"company": company, "isin": "SYNTHETIC0001", "instrument_type": "EQ"},
        )
        source, _ = DataSource.objects.get_or_create(
            source_name="Synthetic FinSight Evaluation Fixture",
            defaults={
                "source_url": "https://example.invalid/finsight-evaluation-fixture",
                "license_terms": "Synthetic data generated for software evaluation; not market or issuer data.",
                "attribution_text": "Synthetic evaluation fixture",
                "refresh_policy": "static_test_fixture",
            },
        )
        published = datetime(2025, 5, 1, tzinfo=timezone.utc)
        document, _ = Document.objects.update_or_create(
            company=company, checksum="finsight-synthetic-evaluation-v1",
            defaults={
                "source": source,
                "document_type": "annual_report",
                "fiscal_period": "FY25",
                "title": "Synthetic Evaluation Report FY25",
                "source_url": "https://example.invalid/finsight-evaluation-report-fy25",
                "published_at": published,
                "status": "active",
            },
        )
        DocumentChunk.objects.update_or_create(
            document=document, chunk_index=0,
            defaults={
                "page_no": 3,
                "section": "Synthetic Management Discussion",
                "text": (
                    "Synthetic evaluation content only. Management described input cost pressure from raw material prices "
                    "and freight as the main operational challenge. The report says production capacity was expanded "
                    "and the outlook depends on stable supply chains. This text is invented for software testing and "
                    "does not describe a real company or actual management statement."
                ),
                "token_count": 48,
            },
        )
        observed_at = datetime(2025, 4, 1, tzinfo=timezone.utc)
        metrics = [
            ("revenue", "FY24", "100", "INR Cr"), ("revenue", "FY25", "125", "INR Cr"),
            ("net_profit", "FY24", "10", "INR Cr"), ("net_profit", "FY25", "15", "INR Cr"),
            ("ebitda", "FY25", "25", "INR Cr"), ("eps", "FY25", "2.5", "INR"),
            ("total_debt", "FY25", "20", "INR Cr"), ("total_equity", "FY25", "40", "INR Cr"),
        ]
        for metric, period, value, unit in metrics:
            MarketObservation.objects.update_or_create(
                company=company, metric=metric, period=period, observed_at=observed_at,
                defaults={
                    "security": security, "value_decimal": Decimal(value), "unit": unit,
                    "source": source, "freshness": "historical",
                    "notes": "Synthetic evaluation value; not a reported issuer fact.",
                },
            )
        for offset, close in enumerate((101, 102, 103, 104, 105)):
            trade_date = datetime(2025, 6, 1, tzinfo=timezone.utc) + timedelta(days=offset)
            MarketObservation.objects.update_or_create(
                company=company, security=security, metric="close_price",
                period=trade_date.strftime("%Y-%m-%d"), observed_at=trade_date,
                defaults={
                    "value_decimal": Decimal(close), "unit": "INR", "source": source,
                    "freshness": "historical", "notes": "Synthetic evaluation price; not a real quote.",
                },
            )
        Announcement.objects.update_or_create(
            company=company, external_id="finsight-demo-board-2025-05",
            defaults={
                "exchange": "TEST", "category": "Board Meeting",
                "headline": "Synthetic board meeting disclosure for evaluation",
                "body": "Synthetic record only; no real corporate disclosure.",
                "published_at": published,
                "source_url": "https://example.invalid/finsight-evaluation-announcement",
            },
        )
        self.stdout.write(self.style.SUCCESS("Synthetic evaluation company FINSIGHTDEMO is ready."))
