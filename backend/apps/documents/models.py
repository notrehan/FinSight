from django.db import models
from apps.companies.models import Company
from apps.market_data.models import DataSource

class Document(models.Model):
    DOC_TYPES = [
        ('annual_report', 'Annual Report'),
        ('earnings_call', 'Earnings Call Transcript'),
        ('presentation', 'Investor Presentation'),
        ('financial_results', 'Financial Results / Filing'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=64, choices=DOC_TYPES, db_index=True)
    fiscal_period = models.CharField(max_length=32, db_index=True)  # FY24, FY25, Q3FY25
    title = models.CharField(max_length=255)
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    source_url = models.URLField(max_length=512)
    checksum = models.CharField(max_length=64, blank=True, default='')
    published_at = models.DateTimeField(db_index=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default='active')

    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['company', 'fiscal_period', 'document_type']),
        ]

    def __str__(self):
        return f"{self.company.legal_name} - {self.title} ({self.fiscal_period})"

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField(db_index=True)
    page_no = models.PositiveIntegerField(null=True, blank=True)
    section = models.CharField(max_length=255, blank=True, default='')
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    vector_key = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        db_table = 'document_chunks'
        unique_together = ('document', 'chunk_index')
        indexes = [
            models.Index(fields=['document', 'page_no']),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of Doc {self.document_id} (p. {self.page_no}, {self.section})"
