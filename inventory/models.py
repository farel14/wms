from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from catalog.models import Product
from warehouse.models import Warehouse


class ImmutableMixin:
    """Create and read only. Existing rows cannot be updated or deleted."""

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("This record is write-once and cannot be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("This record cannot be deleted.")


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stocks")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stocks")
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock"
        unique_together = ("product", "warehouse")
        ordering = ["product__name", "warehouse__code"]

    def __str__(self):
        return f"{self.product} @ {self.warehouse.code} = {self.quantity}"


class InventoryTransaction(models.Model):
    class Type(models.TextChoices):
        IN = "IN", "Stock in"
        OUT = "OUT", "Stock out"
        TRANSFER = "TRANSFER", "Warehouse transfer"
        ADJUST = "ADJUST", "Adjustment"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    number = models.CharField(max_length=32, unique=True)
    transaction_type = models.CharField(max_length=16, choices=Type.choices)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="inventory_transactions"
    )
    destination_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="inventory_transactions")
    quantity = models.IntegerField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="inventory_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inventory_transaction"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if self.pk:
            previous = InventoryTransaction.objects.filter(pk=self.pk).first()
            if previous and previous.status == self.Status.POSTED:
                raise ValidationError("Posted inventory transactions cannot be edited.")
        if not self.number:
            stamp = timezone.localdate().strftime("%Y%m%d")
            prefix = f"TXN-{stamp}-"
            last = InventoryTransaction.objects.filter(number__startswith=prefix).order_by("-number").first()
            seq = 1
            if last:
                seq = int(last.number.rsplit("-", 1)[-1]) + 1
            self.number = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    def clean(self):
        if self.quantity == 0:
            raise ValidationError("Quantity cannot be zero.")
        if self.transaction_type in {self.Type.IN, self.Type.OUT, self.Type.TRANSFER} and self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero for in, out, and transfer.")
        if self.transaction_type == self.Type.TRANSFER:
            if not self.destination_warehouse_id:
                raise ValidationError("A destination warehouse is required for transfers.")
            if self.destination_warehouse_id == self.warehouse_id:
                raise ValidationError("Source and destination warehouses must be different.")
        elif self.destination_warehouse_id:
            raise ValidationError("Destination warehouse is only used for transfers.")


class StockLedger(ImmutableMixin, models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="ledger_entries")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="ledger_entries")
    quantity = models.IntegerField(help_text="Positive increases stock, negative decreases it.")
    balance_after = models.IntegerField()
    inventory_transaction = models.ForeignKey(
        InventoryTransaction, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ledger_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_ledger"
        ordering = ["-created_at", "-id"]
        verbose_name = "stock ledger"
        verbose_name_plural = "stock ledger"

    def __str__(self):
        return f"{self.product} {self.quantity} @ {self.warehouse.code}"
