from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import uuid
from .models import ChatSession, ChatMessage, Watchlist
from .serializers import ChatSessionSerializer, ChatMessageSerializer, WatchlistSerializer

class SessionListView(APIView):
    """
    GET /api/v1/sessions
    POST /api/v1/sessions
    Scoped to authorized user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.pk)
        sessions = ChatSession.objects.filter(user_id=user_id).order_by('-updated_at')
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response({
            'count': len(serializer.data),
            'sessions': serializer.data
        })

    def post(self, request):
        user_id = str(request.user.pk)
        title = request.data.get('title', 'New Research Session')
        session = ChatSession.objects.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title
        )
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class SessionMessagesView(APIView):
    """
    GET /api/v1/sessions/{id}/messages
    Fetch messages for authorized user session.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user_id = str(request.user.pk)
        try:
            session = ChatSession.objects.get(pk=pk)
            # Authorization check
            if session.user_id != user_id:
                return Response({'error': 'Session is unavailable.'}, status=status.HTTP_404_NOT_FOUND)
        except ChatSession.DoesNotExist:
            return Response({'error': f'Session {pk} not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = session.messages.order_by('created_at')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({
            'session_id': pk,
            'title': session.title,
            'count': len(serializer.data),
            'messages': serializer.data
        })

class WatchlistView(APIView):
    """
    GET /api/v1/watchlists
    POST /api/v1/watchlists
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.pk)
        watchlists = Watchlist.objects.filter(user_id=user_id).order_by('-created_at')
        serializer = WatchlistSerializer(watchlists, many=True)
        return Response({'watchlists': serializer.data})

    def post(self, request):
        user_id = str(request.user.pk)
        name = request.data.get('name', 'My Watchlist')
        symbols = request.data.get('symbols', [])
        wl = Watchlist.objects.create(user_id=user_id, name=name, symbols=symbols)
        serializer = WatchlistSerializer(wl)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
