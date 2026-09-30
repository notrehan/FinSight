from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import Company, Security
from .serializers import CompanySerializer

class CompanyListView(APIView):
    """
    GET /api/v1/companies?query=
    Returns companies matching query across legal name, normalized name, or exchange symbol.
    """
    def get(self, request):
        query = request.query_params.get('query', '').strip()
        queryset = Company.objects.prefetch_related('securities').all()
        if query:
            queryset = queryset.filter(
                Q(legal_name__icontains=query) |
                Q(normalized_name__icontains=query) |
                Q(securities__symbol__iexact=query) |
                Q(securities__symbol__icontains=query)
            ).distinct()
        
        serializer = CompanySerializer(queryset[:50], many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })

class CompanyDetailView(APIView):
    """
    GET /api/v1/companies/{id}
    Returns company details and security listings.
    """
    def get(self, request, pk):
        try:
            company = Company.objects.prefetch_related('securities').get(pk=pk)
            serializer = CompanySerializer(company)
            return Response(serializer.data)
        except Company.DoesNotExist:
            return Response({'error': f'Company with id {pk} not found.'}, status=status.HTTP_404_NOT_FOUND)
