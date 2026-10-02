"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from memory import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('api/v1/funds/search', views.fund_search, name='fund-search'),
    path('api/v1/funds/nav/<str:scheme_code>', views.fund_nav, name='fund-nav'),
    path('api/v1/funds/compare', views.fund_compare, name='fund-compare'),
    path('api/v1/macro', views.macro_data, name='macro-data'),
    path('api/v1/documents/<str:company>/<str:document>/pdf', views.source_pdf, name='source-pdf'),
    path('api/v1/ask', views.ask_post, name='ask'),
    path('api/v1/calculate', views.calculate_api, name='calculate'),
    path('api/v1/prices/<str:ticker>', views.price_lookup_api, name='price-lookup'),
    path('api/v1/portfolio/analyze', views.portfolio_analyze, name='portfolio-analyze'),
    path('api/v1/watchlists', views.watchlist_api, name='watchlists'),
    path('api/v1/watchlists/save', views.save_watchlist, name='watchlists-save'),
    path('api/v1/announcements', views.announcements_api, name='announcements'),
    path('api/metrics', views.metrics, name='metrics'),
    path('api/health', views.health, name='health'),
]
