from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect

from accounts.models import log_audit, Audit
from inventory.models import Stock

from .forms import ProductForm
from .models import Product


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        qs = Product.objects.active().annotate(on_hand_qty=Sum("stocks__quantity"))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(unit__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": "New product", "submit_label": "Create product"})
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            user=self.request.user,
            action=Audit.Action.CREATE,
            table_name="Product",
            record_id=self.object.pk,
            description=f"Created product {self.object.name}",
        )
        messages.success(self.request, "Product created.")
        return response

    def get_success_url(self):
        return reverse("product-detail", args=[self.object.pk])


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": f"Edit {self.object.name}", "submit_label": "Save product"})
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            user=self.request.user,
            action=Audit.Action.UPDATE,
            table_name="Product",
            record_id=self.object.pk,
            description=f"Updated product {self.object.name}",
        )
        messages.success(self.request, "Product updated.")
        return response

    def get_success_url(self):
        return reverse("product-detail", args=[self.object.pk])


class ProductDeactivateView(LoginRequiredMixin, View):
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        product.is_active = False
        product.save(update_fields=["is_active"])
        
        log_audit(
            user=self.request.user,
            action=Audit.Action.DEACTIVATE,
            table_name="Product",
            record_id=product.pk,
            description=f"Deactivate product {product.name}",
        )

        return redirect("product-detail", pk=product.pk)


class ProductActivateView(LoginRequiredMixin, View):
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        product.is_active = True
        product.save(update_fields=["is_active"])

        return redirect("product-detail", pk=product.pk)


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = "catalog/product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stocks"] = Stock.objects.filter(product=self.object).select_related("warehouse")
        return context
