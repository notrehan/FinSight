from rest_framework import serializers
from .models import MarketObservation, DataSource

class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'source_name', 'source_url', 'attribution_text', 'refresh_policy']

class MarketObservationSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.source_name', read_only=True)
    source_attribution = serializers.CharField(source='source.attribution_text', read_only=True)

    class Meta:
        model = MarketObservation
        fields = [
            'id', 'company_id', 'security_id', 'metric', 'value_decimal',
            'unit', 'period', 'observed_at', 'fetched_at', 'source_name',
            'source_attribution', 'freshness', 'notes'
        ]
