from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Document, DocumentChunk
from .serializers import DocumentSerializer, DocumentChunkSerializer

class CompanyDocumentsView(APIView):
    """
    GET /api/v1/companies/{id}/documents
    Returns documents available for a company.
    """
    def get(self, request, pk):
        doc_type = request.query_params.get('type')
        period = request.query_params.get('period')
        
        queryset = Document.objects.filter(company_id=pk).order_by('-published_at')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        if period:
            queryset = queryset.filter(fiscal_period=period)
            
        serializer = DocumentSerializer(queryset, many=True)
        return Response({
            'company_id': pk,
            'count': len(serializer.data),
            'documents': serializer.data
        })

class DocumentPassagesView(APIView):
    """
    GET /api/v1/documents/{id}/passages
    Returns chunks/passages for a given document with page/section locators.
    """
    def get(self, request, pk):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response({'error': f'Document {pk} not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        chunks = document.chunks.order_by('chunk_index')
        page_no = request.query_params.get('page')
        if page_no:
            chunks = chunks.filter(page_no=page_no)
            
        serializer = DocumentChunkSerializer(chunks[:100], many=True)
        return Response({
            'document_id': pk,
            'document_title': document.title,
            'company_id': document.company_id,
            'count': len(serializer.data),
            'passages': serializer.data
        })
