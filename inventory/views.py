from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, View

from accounts.models import log_audit, Audit

from .forms import InventoryTransactionForm
from .models import InventoryTransaction, Stock, StockLedger
from .services import post_inventory_transaction, create_inbound_transaction, create_outbound_transaction


class StockListView(LoginRequiredMixin, ListView):
    model = Stock
    template_name = "inventory/stock_list.html"
    context_object_name = "stocks"
    paginate_by = 20

    def get_queryset(self):
        qs = Stock.objects.select_related("product", "warehouse")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(product__name__icontains=q) | Q(warehouse__code__icontains=q) | Q(warehouse__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


class LedgerListView(LoginRequiredMixin, ListView):
    model = StockLedger
    template_name = "inventory/ledger_list.html"
    context_object_name = "entries"
    paginate_by = 20

    def get_queryset(self):
        qs = StockLedger.objects.select_related("product", "warehouse", "inventory_transaction", "created_by")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(product__name__icontains=q)
                | Q(warehouse__code__icontains=q)
                | Q(inventory_transaction__number__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


class TransactionListView(LoginRequiredMixin, ListView):
    model = InventoryTransaction
    template_name = "inventory/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 15


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = InventoryTransaction
    form_class = InventoryTransactionForm
    template_name = "form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": "New inventory transaction", "submit_label": "Save draft"})
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # check if warehouse opname is happening at the moment
        warehouse = form.cleaned_data.get("warehouse")
        notes = form.cleaned_data.get("notes")
        if warehouse and warehouse.is_opname and not self.request.user.is_superuser:
            form.add_error(
                "warehouse",
                "Cannot create transactions during stock opname.",
            )
            return self.form_invalid(form)
        
        destination_warehouse = form.cleaned_data.get("destination_warehouse")
        if destination_warehouse and destination_warehouse.is_opname and not self.request.user.is_superuser:
            form.add_error(
                "destination_warehouse",
                "Cannot create transactions during stock opname.",
            )
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        log_audit(
            user=self.request.user,
            action=Audit.Action.CREATE,
            table_name="InventoryTransaction",
            record_id=self.object.pk,
            description=f"Created {self.object.number}",
        )
        if form.cleaned_data.get("transaction_type") == InventoryTransaction.Type.IN:
            supplier_name = form.cleaned_data.get("supplier_name")
            expected_date = form.cleaned_data.get("expected_date")
            with transaction.atomic():
                create_inbound_transaction(
                    warehouse=warehouse,
                    expected_date=expected_date,
                    notes=notes,
                    supplier_name=supplier_name,
                    user=self.request.user
                )
        elif form.cleaned_data.get("transaction_type") == InventoryTransaction.Type.OUT:
            customer_name = form.cleaned_data.get("customer_name")
            required_date = form.cleaned_data.get("required_date")
            with transaction.atomic():
                create_outbound_transaction(
                    warehouse=warehouse,
                required_date=required_date,
                notes=notes,
                customer_name=customer_name,
                user=self.request.user
            )
        log_audit(
            user=self.request.user,
            action=Audit.Action.CREATE,
            table_name="InventoryTransaction",
            record_id=self.object.pk,
            description=f"Created {self.object.number}",
        )
        messages.success(self.request, "Draft transaction saved. Post it to update stock.")
        return response

    def get_success_url(self):
        return reverse("transaction-detail", args=[self.object.pk])


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = InventoryTransaction
    template_name = "inventory/transaction_detail.html"


class TransactionPostView(LoginRequiredMixin, View):
    def post(self, request, pk):
        txn = get_object_or_404(InventoryTransaction, pk=pk)
        try:
            post_inventory_transaction(txn, request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"{txn.number} posted. Stock and ledger updated.")
        return redirect("transaction-detail", pk=pk)
