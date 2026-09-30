from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import MarketObservation
from .serializers import MarketObservationSerializer

class CompanyMetricsView(APIView):
    """
    GET /api/v1/companies/{id}/metrics
    Returns historical observations/metrics for a company.
    Filterable by metric, period, or date range.
    """
    def get(self, request, pk):
        metric = request.query_params.get('metric')
        period = request.query_params.get('period')
        
        queryset = MarketObservation.objects.filter(company_id=pk).select_related('source').order_by('-observed_at')
        if metric:
            queryset = queryset.filter(metric=metric)
        if period:
            queryset = queryset.filter(period=period)
            
        serializer = MarketObservationSerializer(queryset[:100], many=True)
        return Response({
            'company_id': pk,
            'count': len(serializer.data),
            'metrics': serializer.data
        })
