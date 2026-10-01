from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Announcement
from .serializers import AnnouncementSerializer

class AnnouncementListView(APIView):
    """
    GET /api/v1/announcements
    Search and filter announcements by company_id, symbol, exchange, category, or date.
    """
    def get(self, request):
        company_id = request.query_params.get('company_id')
        symbol = request.query_params.get('symbol')
        exchange = request.query_params.get('exchange')
        category = request.query_params.get('category')
        query = request.query_params.get('query')

        queryset = Announcement.objects.select_related('company').prefetch_related('company__securities').all()
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if symbol:
            queryset = queryset.filter(company__securities__symbol__iexact=symbol)
        if exchange:
            queryset = queryset.filter(exchange__iexact=exchange)
        if category:
            queryset = queryset.filter(category__iexact=category)
        if query:
            queryset = queryset.filter(headline__icontains=query)

        serializer = AnnouncementSerializer(queryset[:50], many=True)
        return Response({
            'count': len(serializer.data),
            'announcements': serializer.data
        })
