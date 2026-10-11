from django.contrib import admin

from .models import Audit


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "table_name", "record_id", "description")
    list_filter = ("action", "table_name")
    search_fields = ("description", "user__username", "record_id")
    readonly_fields = ("user", "action", "table_name", "record_id", "description", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
