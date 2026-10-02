from django.contrib import admin
from .models import Announcement, EvaluationScore, FundFactsheet, FundNav, MacroObservation, PromptVersion, Watchlist

@admin.register(FundFactsheet)
class FundFactsheetAdmin(admin.ModelAdmin):
    list_display = ("scheme_code", "scheme_name", "category", "expense_ratio", "latest_nav", "nav_date", "updated_at")
    search_fields = ("scheme_code", "scheme_name", "category")


@admin.register(FundNav)
class FundNavAdmin(admin.ModelAdmin):
    list_display = ("scheme_code", "date", "nav", "source_url")
    list_filter = ("date",)
    search_fields = ("scheme_code",)


@admin.register(MacroObservation)
class MacroObservationAdmin(admin.ModelAdmin):
    list_display = ("series", "period", "value", "unit", "observed_at")
    list_filter = ("series", "unit")
    search_fields = ("series", "period")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("ticker", "published_at", "category", "approval_status", "headline")
    list_filter = ("category", "approval_status", "source")
    search_fields = ("ticker", "headline", "external_id")


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("name", "owner_key", "created_at")
    search_fields = ("name", "owner_key")


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "active", "created_at")
    list_filter = ("active",)


@admin.register(EvaluationScore)
class EvaluationScoreAdmin(admin.ModelAdmin):
    list_display = ("prompt_version", "dataset", "metric", "score", "created_at")
    list_filter = ("prompt_version", "dataset", "metric")
