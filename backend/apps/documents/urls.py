from django.urls import path
from .views import CompanyDocumentsView, DocumentPassagesView

urlpatterns = [
    path('companies/<int:pk>/documents', CompanyDocumentsView.as_view(), name='company-documents'),
    path('documents/<int:pk>/passages', DocumentPassagesView.as_view(), name='document-passages'),
]
