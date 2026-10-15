from django.contrib import admin

from .models import InventoryTransaction, Stock, StockLedger


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "updated_at")
    list_filter = ("warehouse",)
    search_fields = ("product__name", "warehouse__code")
    readonly_fields = ("product", "warehouse", "quantity", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "warehouse", "quantity", "balance_after", "inventory_transaction")
    list_filter = ("warehouse",)
    search_fields = ("product__name", "inventory_transaction__number")
    readonly_fields = (
        "product",
        "warehouse",
        "quantity",
        "balance_after",
        "inventory_transaction",
        "created_by",
        "created_at",
    )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("number", "transaction_type", "product", "warehouse", "quantity", "status", "created_at")
    list_filter = ("transaction_type", "status", "warehouse")
    search_fields = ("number", "product__name")
    readonly_fields = ("number", "status", "created_at", "posted_at")
