from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, View

from inventory.services import pick_stock, receive_stock

from .forms import (
    InboundLineForm,
    InboundShipmentForm,
    OutboundLineForm,
    OutboundOrderForm,
    PickLineForm,
    ReceiveLineForm,
)
from .models import InboundLine, InboundShipment, OutboundLine, OutboundOrder


class InboundListView(LoginRequiredMixin, ListView):
    model = InboundShipment
    template_name = "operations/inbound_list.html"
    context_object_name = "shipments"
    paginate_by = 25


class InboundCreateView(LoginRequiredMixin, CreateView):
    model = InboundShipment
    form_class = InboundShipmentForm
    template_name = "form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Inbound shipment created.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": "New inbound shipment", "submit_label": "Create inbound"})
        return context

    def get_success_url(self):
        return reverse("inbound-detail", args=[self.object.pk])


class InboundDetailView(LoginRequiredMixin, DetailView):
    model = InboundShipment
    template_name = "operations/inbound_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["line_form"] = InboundLineForm()
        context["receive_form"] = ReceiveLineForm(warehouse=self.object.warehouse)
        return context


class InboundAddLineView(LoginRequiredMixin, View):
    def post(self, request, pk):
        shipment = get_object_or_404(InboundShipment, pk=pk)
        if shipment.status in {InboundShipment.Status.COMPLETED, InboundShipment.Status.CANCELLED}:
            messages.error(request, "This inbound can no longer be edited.")
            return redirect("inbound-detail", pk=pk)
        form = InboundLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.shipment = shipment
            if InboundLine.objects.filter(shipment=shipment, product=line.product).exists():
                messages.error(request, "That SKU is already on this inbound.")
            else:
                line.save()
                messages.success(request, "Line added.")
        else:
            messages.error(request, "Could not add line.")
        return redirect("inbound-detail", pk=pk)


class InboundReceiveLineView(LoginRequiredMixin, View):
    def post(self, request, pk, line_id):
        shipment = get_object_or_404(InboundShipment, pk=pk)
        line = get_object_or_404(InboundLine, pk=line_id, shipment=shipment)
        if shipment.status == InboundShipment.Status.CANCELLED:
            messages.error(request, "Cancelled inbounds cannot be received.")
            return redirect("inbound-detail", pk=pk)
        form = ReceiveLineForm(request.POST, warehouse=shipment.warehouse)
        if not form.is_valid():
            messages.error(request, "Provide a valid quantity and putaway location.")
            return redirect("inbound-detail", pk=pk)
        qty = form.cleaned_data["quantity"]
        location = form.cleaned_data["location"]
        if location.warehouse_id != shipment.warehouse_id:
            messages.error(request, "Putaway location must belong to this warehouse.")
            return redirect("inbound-detail", pk=pk)
        if qty > line.remaining():
            messages.error(request, "Cannot receive more than the remaining expected quantity.")
            return redirect("inbound-detail", pk=pk)
        try:
            with transaction.atomic():
                receive_stock(
                    product=line.product,
                    location=location,
                    quantity=qty,
                    user=request.user,
                    reference=shipment.number,
                )
                line.received_qty += qty
                line.putaway_location = location
                line.save(update_fields=["received_qty", "putaway_location"])
                if shipment.status == InboundShipment.Status.DRAFT:
                    shipment.status = InboundShipment.Status.RECEIVING
                    shipment.save(update_fields=["status"])
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"Received {qty} {line.product.unit} of {line.product.sku}.")
        return redirect("inbound-detail", pk=pk)


class InboundCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        shipment = get_object_or_404(InboundShipment, pk=pk)
        if not shipment.lines.exists():
            messages.error(request, "Add at least one line before completing.")
            return redirect("inbound-detail", pk=pk)
        if shipment.lines.filter(received_qty=0).exists():
            messages.error(request, "Receive every line before completing this inbound.")
            return redirect("inbound-detail", pk=pk)
        shipment.status = InboundShipment.Status.COMPLETED
        shipment.received_at = timezone.now()
        shipment.save(update_fields=["status", "received_at"])
        messages.success(request, f"{shipment.number} marked complete.")
        return redirect("inbound-detail", pk=pk)


class OutboundListView(LoginRequiredMixin, ListView):
    model = OutboundOrder
    template_name = "operations/outbound_list.html"
    context_object_name = "orders"
    paginate_by = 25


class OutboundCreateView(LoginRequiredMixin, CreateView):
    model = OutboundOrder
    form_class = OutboundOrderForm
    template_name = "form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Outbound order created.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": "New outbound order", "submit_label": "Create outbound"})
        return context

    def get_success_url(self):
        return reverse("outbound-detail", args=[self.object.pk])


class OutboundDetailView(LoginRequiredMixin, DetailView):
    model = OutboundOrder
    template_name = "operations/outbound_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["line_form"] = OutboundLineForm()
        lines = list(self.object.lines.select_related("product", "pick_location"))
        for line in lines:
            line.pick_form = PickLineForm(warehouse=self.object.warehouse, product=line.product)
        context["lines"] = lines
        return context


class OutboundAddLineView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(OutboundOrder, pk=pk)
        if order.status in {OutboundOrder.Status.SHIPPED, OutboundOrder.Status.CANCELLED}:
            messages.error(request, "This outbound can no longer be edited.")
            return redirect("outbound-detail", pk=pk)
        form = OutboundLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.order = order
            if OutboundLine.objects.filter(order=order, product=line.product).exists():
                messages.error(request, "That SKU is already on this outbound.")
            else:
                line.save()
                messages.success(request, "Line added.")
        else:
            messages.error(request, "Could not add line.")
        return redirect("outbound-detail", pk=pk)


class OutboundPickLineView(LoginRequiredMixin, View):
    def post(self, request, pk, line_id):
        order = get_object_or_404(OutboundOrder, pk=pk)
        line = get_object_or_404(OutboundLine, pk=line_id, order=order)
        form = PickLineForm(request.POST, warehouse=order.warehouse, product=line.product)
        if not form.is_valid():
            messages.error(request, "Provide a valid quantity and pick location with stock.")
            return redirect("outbound-detail", pk=pk)
        qty = form.cleaned_data["quantity"]
        location = form.cleaned_data["location"]
        if qty > line.remaining():
            messages.error(request, "Cannot pick more than the remaining requested quantity.")
            return redirect("outbound-detail", pk=pk)
        try:
            with transaction.atomic():
                pick_stock(
                    product=line.product,
                    location=location,
                    quantity=qty,
                    user=request.user,
                    reference=order.number,
                )
                line.picked_qty += qty
                line.pick_location = location
                line.save(update_fields=["picked_qty", "pick_location"])
                if order.status == OutboundOrder.Status.DRAFT:
                    order.status = OutboundOrder.Status.PICKING
                    order.save(update_fields=["status"])
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"Picked {qty} {line.product.unit} of {line.product.sku}.")
        return redirect("outbound-detail", pk=pk)


class OutboundShipView(LoginRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(OutboundOrder, pk=pk)
        if not order.lines.exists():
            messages.error(request, "Add at least one line before shipping.")
            return redirect("outbound-detail", pk=pk)
        short = [line for line in order.lines.all() if line.picked_qty < line.requested_qty]
        if short:
            messages.error(request, "Pick every line before shipping.")
            return redirect("outbound-detail", pk=pk)
        order.status = OutboundOrder.Status.SHIPPED
        order.shipped_at = timezone.now()
        order.save(update_fields=["status", "shipped_at"])
        messages.success(request, f"{order.number} shipped.")
        return redirect("outbound-detail", pk=pk)
