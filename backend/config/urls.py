"""
FinSight AI URL Configuration.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='research-app'),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/v1/', include('apps.assistant.urls')),
    path('api/v1/', include('apps.companies.urls')),
    path('api/v1/', include('apps.sessions.urls')),
    path('api/v1/', include('apps.announcements.urls')),
    path('api/v1/', include('apps.market_data.urls')),
    path('api/v1/', include('apps.documents.urls')),
]
