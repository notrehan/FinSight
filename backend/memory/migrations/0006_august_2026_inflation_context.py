from datetime import datetime
from decimal import Decimal

from django.db import migrations


OBSERVATIONS = (
    ("CPI Inflation (Combined, YoY)", "4.82", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2310058&lang=1&reg=19", "2026-09-14T16:00:00+05:30"),
    ("WPI Inflation (All Commodities, YoY)", "9.92", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2309977&lang=1&reg=3", "2026-09-14T12:01:00+05:30"),
)


def add_inflation_rows(apps, schema_editor):
    MacroObservation = apps.get_model("memory", "MacroObservation")
    db = schema_editor.connection.alias
    for series, value, source, observed in OBSERVATIONS:
        MacroObservation.objects.using(db).update_or_create(series=series, period="2026-08", source_url=source,
            defaults={"value": Decimal(value), "unit": "percent", "observed_at": datetime.fromisoformat(observed)})


def remove_inflation_rows(apps, schema_editor):
    MacroObservation = apps.get_model("memory", "MacroObservation")
    MacroObservation.objects.using(schema_editor.connection.alias).filter(series__in=[row[0] for row in OBSERVATIONS], period="2026-08").delete()


class Migration(migrations.Migration):
    dependencies = [("memory", "0005_promptversion_evaluationscore")]
    operations = [migrations.RunPython(add_inflation_rows, remove_inflation_rows)]
