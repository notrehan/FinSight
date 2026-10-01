from django.db import models
from apps.companies.models import Company

class Announcement(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='announcements')
    exchange = models.CharField(max_length=16, db_index=True)  # NSE, BSE
    external_id = models.CharField(max_length=128, blank=True, default='')
    category = models.CharField(max_length=64, db_index=True)  # Results, Board Meeting, Acquisition, Fundraise, Regulatory
    headline = models.CharField(max_length=512)
    body = models.TextField(blank=True, default='')
    published_at = models.DateTimeField(db_index=True)
    source_url = models.URLField(max_length=512)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['published_at']),
        ]

    def __str__(self):
        return f"{self.company.legal_name} [{self.category}] {self.headline[:60]}"
