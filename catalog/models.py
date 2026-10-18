from django.db import models
from django.db.models import Sum


def next_sku(model, prefix="SKU", field="sku"):
    head = f"{prefix}-"
    last = model.objects.filter(**{f"{field}__startswith": head}).order_by("-created_at").first()
    seq = 1
    if last:
        seq = int(getattr(last, field).rsplit("-", 1)[-1]) + 1
    return f"{head}{seq:03d}"

class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=16)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
