from django.db import models
from django.db.models import Sum
from core.models import ActiveQuerySet


def next_sku(model, prefix="SKU", field="sku"):
    head = f"{prefix}-"
    last = model.objects.filter(**{f"{field}__startswith": head}).order_by("-created_at").first()
    seq = 1
    if last:
        seq = int(getattr(last, field).rsplit("-", 1)[-1]) + 1
    return f"{head}{seq:03d}"

class Product(models.Model):
    
    class MeasurementUnit(models.TextChoices):
        EA = "EA", "Each"
        PK = "PK", "Pack"
        CS = "CS", "Case"
        PLT = "PLT", "Pallet"
        
    UNIT_TO_EACH = {
        MeasurementUnit.EA: 1.0,
        MeasurementUnit.PK: 6.0,
        MeasurementUnit.CS: 24.0,
        MeasurementUnit.PLT: 1200.0,
    }
    
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=16, choices=MeasurementUnit.choices, default=MeasurementUnit.EA)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ActiveQuerySet.as_manager()
    class Meta:
        db_table = "product"
        ordering = ["name"]

    def __str__(self):
        return f"{self.sku} - {self.name} ({self.unit})"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = next_sku(Product, "SKU")
        super().save(*args, **kwargs)

    @property
    def on_hand(self):
        return self.stocks.aggregate(total=Sum("quantity"))["total"] or 0
