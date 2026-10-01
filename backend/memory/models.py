from django.db import models


class Conversation(models.Model):
    session_id = models.UUIDField(unique=True)
    company = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company} - {self.session_id}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class FundFactsheet(models.Model):
    scheme_code = models.CharField(max_length=32, unique=True)
    scheme_name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    expense_ratio = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    holdings = models.JSONField(default=dict, blank=True)
    latest_nav = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    nav_date = models.DateField(null=True, blank=True)
    source_url = models.URLField(max_length=512)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.scheme_name} ({self.scheme_code})"


class FundNav(models.Model):
    scheme_code = models.CharField(max_length=32, db_index=True)
    date = models.DateField(db_index=True)
    nav = models.DecimalField(max_digits=16, decimal_places=6)
    source_url = models.URLField(max_length=512)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["scheme_code", "date"], name="unique_fund_nav_date")]


class MacroObservation(models.Model):
    series = models.CharField(max_length=128, db_index=True)
    period = models.CharField(max_length=32, db_index=True)
    value = models.DecimalField(max_digits=20, decimal_places=6)
    unit = models.CharField(max_length=32)
    source_url = models.URLField(max_length=512)
    observed_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["series", "period", "source_url"], name="unique_macro_source_period")]

    def __str__(self):
        return f"{self.series} {self.period}: {self.value} {self.unit}"


class Watchlist(models.Model):
    owner_key = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=100, default="My watchlist")
    tickers = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class Announcement(models.Model):
    CATEGORY_CHOICES = [(value, value.replace("_", " ").title()) for value in ("results", "board_changes", "pledges", "fundraises", "other")]
    ticker = models.CharField(max_length=32, db_index=True)
    headline = models.CharField(max_length=512)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="other", db_index=True)
    summary = models.TextField(blank=True)
    source = models.CharField(max_length=32)
    source_url = models.URLField(max_length=512)
    external_id = models.CharField(max_length=128, unique=True)
    published_at = models.DateTimeField(db_index=True)
    approval_status = models.CharField(max_length=16, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PromptVersion(models.Model):
    version = models.CharField(max_length=32, unique=True)
    system_prompt = models.TextField()
    active = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.version


class EvaluationScore(models.Model):
    prompt_version = models.ForeignKey(PromptVersion, on_delete=models.CASCADE, related_name="scores")
    dataset = models.CharField(max_length=100)
    metric = models.CharField(max_length=64)
    score = models.DecimalField(max_digits=8, decimal_places=5)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
