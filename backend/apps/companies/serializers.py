from rest_framework import serializers
from .models import Company, Security

class SecuritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Security
        fields = ['id', 'exchange', 'symbol', 'isin', 'instrument_type', 'active_from', 'active_to']

class CompanySerializer(serializers.ModelSerializer):
    securities = SecuritySerializer(many=True, read_only=True)
    
    class Meta:
        model = Company
        fields = [
            'id', 'legal_name', 'normalized_name', 'sector',
            'industry', 'identifiers_json', 'description', 'created_at', 'securities'
        ]
