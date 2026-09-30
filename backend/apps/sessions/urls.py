from django.urls import path
from .views import SessionListView, SessionMessagesView, WatchlistView

urlpatterns = [
    path('sessions', SessionListView.as_view(), name='session-list'),
    path('sessions/<str:pk>/messages', SessionMessagesView.as_view(), name='session-messages'),
    path('watchlists', WatchlistView.as_view(), name='watchlist-list'),
]
