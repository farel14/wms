from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Sum
from django.views.generic import ListView, TemplateView

from catalog.models import Product
from inventory.models import InventoryTransaction, Stock, StockLedger
from warehouse.models import Warehouse

from .models import Audit


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "warehouse_count": Warehouse.objects.count(),
                "product_count": Product.objects.count(),
                "on_hand": Stock.objects.aggregate(total=Sum("quantity"))["total"] or 0,
                "draft_txns": InventoryTransaction.objects.filter(status=InventoryTransaction.Status.DRAFT).count(),
                "posted_txns": InventoryTransaction.objects.filter(status=InventoryTransaction.Status.POSTED).count(),
                "recent_ledger": StockLedger.objects.select_related("product", "warehouse", "inventory_transaction")[:8],
                "recent_audit": Audit.objects.select_related("user")[:8],
                "recent_txns": InventoryTransaction.objects.select_related("product", "warehouse", "created_by")[:8],
            }
        )
        return context


class AuditListView(LoginRequiredMixin, ListView):
    model = Audit
    template_name = "accounts/audit_list.html"
    context_object_name = "entries"
    paginate_by = 20


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    queryset = User.objects.order_by("username").prefetch_related("groups")

    def get_queryset(self):
        users = super().get_queryset()

        for user in users:
            user.group_names = ", ".join(
                user.groups.values_list("name", flat=True)
            )

        return users