from rest_framework import serializers
from .models import ChatSession, ChatMessage, Watchlist

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session_id', 'role', 'content', 'schema_version',
            'trace_id', 'safety_label', 'citations_json', 'numeric_claims_json',
            'limitations_json', 'tool_trace_json', 'created_at'
        ]

class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(source='messages.count', read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'user_id', 'title', 'message_count', 'last_message', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last = obj.messages.last()
        return last.content[:80] if last else ''

class WatchlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Watchlist
        fields = ['id', 'user_id', 'name', 'symbols', 'created_at']
