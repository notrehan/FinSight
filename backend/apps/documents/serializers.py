from rest_framework import serializers
from .models import Document, DocumentChunk

class DocumentChunkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    source_url = serializers.CharField(source='document.source_url', read_only=True)

    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'document_id', 'document_title', 'chunk_index',
            'page_no', 'section', 'text', 'token_count', 'source_url'
        ]

class DocumentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.legal_name', read_only=True)
    chunk_count = serializers.IntegerField(source='chunks.count', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'company_id', 'company_name', 'document_type',
            'fiscal_period', 'title', 'source_url', 'checksum',
            'published_at', 'ingested_at', 'status', 'chunk_count'
        ]
