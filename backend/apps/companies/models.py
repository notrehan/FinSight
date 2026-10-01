from django.db import models

class Company(models.Model):
    legal_name = models.CharField(max_length=255, db_index=True)
    normalized_name = models.CharField(max_length=255, db_index=True)
    sector = models.CharField(max_length=128, db_index=True)
    industry = models.CharField(max_length=128, blank=True, default='')
    identifiers_json = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.legal_name

class Security(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='securities')
    exchange = models.CharField(max_length=16, db_index=True)  # NSE, BSE
    symbol = models.CharField(max_length=32, db_index=True)
    isin = models.CharField(max_length=32, db_index=True)
    instrument_type = models.CharField(max_length=32, default='EQ')
    active_from = models.DateField(null=True, blank=True)
    active_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'securities'
        verbose_name_plural = 'securities'
        unique_together = ('exchange', 'symbol')

    def __str__(self):
        return f"{self.exchange}:{self.symbol} ({self.isin})"
