from django.urls import path
from .views import CompanyMetricsView

urlpatterns = [
    path('companies/<int:pk>/metrics', CompanyMetricsView.as_view(), name='company-metrics'),
]
