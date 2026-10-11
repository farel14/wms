from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import log_audit
from inventory.models import Stock

from .forms import WarehouseForm
from .models import Warehouse


class WarehouseListView(LoginRequiredMixin, ListView):
    model = Warehouse
    template_name = "warehouse/list.html"
    context_object_name = "warehouses"


class WarehouseCreateView(LoginRequiredMixin, CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": "New warehouse", "submit_label": "Create warehouse"})
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            user=self.request.user,
            action="CREATE",
            table_name="Warehouse",
            record_id=self.object.pk,
            description=f"Created warehouse {self.object.code}",
        )
        messages.success(self.request, "Warehouse created.")
        return response

    def get_success_url(self):
        return reverse("warehouse-detail", args=[self.object.pk])


class WarehouseUpdateView(LoginRequiredMixin, UpdateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = "form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": f"Edit {self.object.code}", "submit_label": "Save warehouse"})
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            user=self.request.user,
            action="UPDATE",
            table_name="Warehouse",
            record_id=self.object.pk,
            description=f"Updated warehouse {self.object.code}",
        )
        messages.success(self.request, "Warehouse updated.")
        return response

    def get_success_url(self):
        return reverse("warehouse-detail", args=[self.object.pk])


class WarehouseDetailView(LoginRequiredMixin, DetailView):
    model = Warehouse
    template_name = "warehouse/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stocks"] = Stock.objects.filter(warehouse=self.object, quantity__gt=0).select_related("product")
        return context
