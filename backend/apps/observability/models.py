from django.db import models

class ToolRun(models.Model):
    trace_id = models.CharField(max_length=128, db_index=True)
    tool_name = models.CharField(max_length=64, db_index=True)
    input_hash = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=32, default='success')  # success, error, skipped
    duration_ms = models.FloatField(default=0.0)
    source_id = models.CharField(max_length=128, blank=True, default='')
    error_code = models.CharField(max_length=64, blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tool_runs'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.tool_name}] {self.status} ({self.duration_ms:.1f}ms) - {self.trace_id[:8]}"

class PromptVersion(models.Model):
    name = models.CharField(max_length=64)
    version = models.CharField(max_length=32, unique=True)
    template_hash = models.CharField(max_length=64, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    active_flag = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prompt_versions'

    def __str__(self):
        return f"{self.name} ({self.version}) - active: {self.active_flag}"
