from django.db import models
from apps.companies.models import Company, Security

class DataSource(models.Model):
    source_name = models.CharField(max_length=128, unique=True)
    source_url = models.URLField(max_length=512)
    license_terms = models.TextField(blank=True, default='')
    attribution_text = models.CharField(max_length=255)
    refresh_policy = models.CharField(max_length=128, default='daily_batch')

    class Meta:
        db_table = 'data_sources'

    def __str__(self):
        return self.source_name

class MarketObservation(models.Model):
    FRESHNESS_CHOICES = [
        ('current', 'Current'),
        ('delayed', 'Delayed'),
        ('stale', 'Stale'),
        ('historical', 'Historical'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='observations')
    security = models.ForeignKey(Security, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations')
    metric = models.CharField(max_length=64, db_index=True)  # revenue, operating_profit, net_profit, close_price, eps, pe_ratio, debt_to_equity, market_cap
    value_decimal = models.DecimalField(max_digits=20, decimal_places=4)
    unit = models.CharField(max_length=32, default='INR')     # INR, INR Cr, Ratio, Percentage, Shares
    period = models.CharField(max_length=32, db_index=True)   # FY24, FY25, Q3FY25, 2026-03-28
    observed_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    freshness = models.CharField(max_length=16, choices=FRESHNESS_CHOICES, default='historical')
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'market_observations'
        indexes = [
            models.Index(fields=['company', 'metric', 'period']),
            models.Index(fields=['security', 'observed_at']),
        ]

    def __str__(self):
        return f"{self.company.legal_name} | {self.metric} | {self.period}: {self.value_decimal} {self.unit}"
