from datetime import datetime
from decimal import Decimal

from django.db import migrations, models


SOURCE = "https://m.rbi.org.in/home.aspx"
OBSERVED_AT = datetime.fromisoformat("2026-10-01T13:00:00+05:30")
STARTER_RATES = (
    ("Policy Repo Rate", "5.25"),
    ("Standing Deposit Facility Rate", "5.00"),
    ("Marginal Standing Facility Rate", "5.50"),
    ("Bank Rate", "5.50"),
    ("Fixed Reverse Repo Rate", "3.35"),
    ("Cash Reserve Ratio", "3.00"),
    ("Statutory Liquidity Ratio", "18.00"),
)


def load_starter_rates(apps, schema_editor):
    MacroObservation = apps.get_model("memory", "MacroObservation")
    for series, value in STARTER_RATES:
        MacroObservation.objects.using(schema_editor.connection.alias).update_or_create(
            series=series, period="2026-10-01", source_url=SOURCE,
            defaults={"value": Decimal(value), "unit": "percent", "observed_at": OBSERVED_AT},
        )


def remove_starter_rates(apps, schema_editor):
    apps.get_model("memory", "MacroObservation").objects.using(schema_editor.connection.alias).filter(
        source_url=SOURCE, period="2026-10-01", series__in=[name for name, _ in STARTER_RATES],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("memory", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="FundFactsheet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheme_code", models.CharField(max_length=32, unique=True)),
                ("scheme_name", models.CharField(max_length=255)),
                ("category", models.CharField(blank=True, max_length=120)),
                ("expense_ratio", models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True)),
                ("holdings", models.JSONField(blank=True, default=dict)),
                ("latest_nav", models.DecimalField(blank=True, decimal_places=6, max_digits=16, null=True)),
                ("nav_date", models.DateField(blank=True, null=True)),
                ("source_url", models.URLField(max_length=512)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="FundNav",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheme_code", models.CharField(db_index=True, max_length=32)),
                ("date", models.DateField(db_index=True)),
                ("nav", models.DecimalField(decimal_places=6, max_digits=16)),
                ("source_url", models.URLField(max_length=512)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("scheme_code", "date"), name="unique_fund_nav_date")]},
        ),
        migrations.CreateModel(
            name="MacroObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("series", models.CharField(db_index=True, max_length=128)),
                ("period", models.CharField(db_index=True, max_length=32)),
                ("value", models.DecimalField(decimal_places=6, max_digits=20)),
                ("unit", models.CharField(max_length=32)),
                ("source_url", models.URLField(max_length=512)),
                ("observed_at", models.DateTimeField()),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("series", "period", "source_url"), name="unique_macro_source_period")]},
        ),
        migrations.RunPython(load_starter_rates, remove_starter_rates),
    ]
