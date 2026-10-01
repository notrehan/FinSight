from rest_framework import serializers
from .models import Announcement

class AnnouncementSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.legal_name', read_only=True)
    company_symbol = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'company_id', 'company_name', 'company_symbol', 'exchange',
            'external_id', 'category', 'headline', 'body',
            'published_at', 'source_url', 'fetched_at'
        ]

    def get_company_symbol(self, obj):
        first_sec = obj.company.securities.first()
        return first_sec.symbol if first_sec else ''
