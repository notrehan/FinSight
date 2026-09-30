from django.urls import path
from .views import AskAssistantView, HealthCheckView, PortfolioAnalyzeView, MutualFundsFactsheetView

urlpatterns = [
    path('assistant/ask', AskAssistantView.as_view(), name='assistant-ask'),
    path('health', HealthCheckView.as_view(), name='health-check'),
    path('portfolio/analyze', PortfolioAnalyzeView.as_view(), name='portfolio-analyze'),
    path('funds', MutualFundsFactsheetView.as_view(), name='funds-factsheet'),
]
