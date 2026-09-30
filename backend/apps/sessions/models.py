import uuid
from django.db import models

class ChatSession(models.Model):
    id = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=128, default='default_user', db_index=True)
    title = models.CharField(max_length=255, default='New Research Session')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.id[:8]})"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16)  # 'user', 'assistant', 'system'
    content = models.TextField()
    schema_version = models.CharField(max_length=32, default='v1.2-grounded')
    trace_id = models.CharField(max_length=128, blank=True, default='', db_index=True)
    safety_label = models.CharField(max_length=32, blank=True, default='factual_research')
    citations_json = models.JSONField(default=list, blank=True)
    numeric_claims_json = models.JSONField(default=list, blank=True)
    limitations_json = models.JSONField(default=list, blank=True)
    tool_trace_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:40]} ({self.session_id[:8]})"

class Watchlist(models.Model):
    user_id = models.CharField(max_length=128, default='default_user', db_index=True)
    name = models.CharField(max_length=128)
    symbols = models.JSONField(default=list)  # list of exchange symbols or company IDs
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'watchlists'

    def __str__(self):
        return f"{self.name} ({len(self.symbols)} items)"
