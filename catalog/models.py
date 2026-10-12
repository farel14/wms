from django.db import models
from django.db.models import Sum


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

    @property
    def on_hand(self):
        return self.stocks.aggregate(total=Sum("quantity"))["total"] or 0
