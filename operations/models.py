from django.conf import settings
from django.db import models
from django.utils import timezone

from catalog.models import Product
from warehouse.models import Warehouse


def next_document_number(model, prefix, field="number"):
    stamp = timezone.localdate().strftime("%Y%m%d")
    head = f"{prefix}-{stamp}-"
    last = model.objects.filter(**{f"{field}__startswith": head}).order_by(f"-{field}").first()
    seq = 1
    if last:
        seq = int(getattr(last, field).rsplit("-", 1)[-1]) + 1
    return f"{head}{seq:04d}"


class InboundShipment(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECEIVING = "RECEIVING", "Receiving"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=32, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="inbound_shipments")
    supplier_name = models.CharField(max_length=160)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_inbounds"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = next_document_number(InboundShipment, "INB")
        super().save(*args, **kwargs)


class InboundLine(models.Model):
    shipment = models.ForeignKey(InboundShipment, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    expected_qty = models.PositiveIntegerField()
    received_qty = models.PositiveIntegerField(default=0)
    putaway_location = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ("shipment", "product")

    def remaining(self):
        return max(self.expected_qty - self.received_qty, 0)


class OutboundOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PICKING = "PICKING", "Picking"
        SHIPPED = "SHIPPED", "Shipped"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=32, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="outbound_orders")
    customer_name = models.CharField(max_length=160)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    required_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_outbounds"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = next_document_number(OutboundOrder, "OUT")
        super().save(*args, **kwargs)


class OutboundLine(models.Model):
    order = models.ForeignKey(OutboundOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    requested_qty = models.PositiveIntegerField()
    picked_qty = models.PositiveIntegerField(default=0)
    pick_location = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ("order", "product")

    def remaining(self):
        return max(self.requested_qty - self.picked_qty, 0)
