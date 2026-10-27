from django.db import models
from django.db.models import Sum


class Warehouse(models.Model):
    code = models.CharField("warehouse code", max_length=16, unique=True)
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=255)
    is_opname = models.BooleanField(default=False)

    class Meta:
        db_table = "warehouse"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    @property
    def on_hand(self):
        return self.stocks.aggregate(total=Sum("quantity"))["total"] or 0

# Location of the product in the warehouse, e.g. A1, B2, etc.
class Location(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="locations")
    code = models.CharField(max_length=32)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "location"
        unique_together = ("warehouse", "code")
        ordering = ["warehouse__name", "code"]

    def __str__(self):
        return f"{self.code} ({self.warehouse.name})"
