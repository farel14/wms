from django.db import models
from django.db.models import Sum
from catalog.utils import convert_to_unit
from catalog.models import Product
from core.models import TimestampedModel


class Warehouse(TimestampedModel):
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
    
    @property
    def on_hand_each(self):
        stocks = self.stocks.values_list("quantity", "product__unit")
        
        stock_count = 0
        
        if not stocks.exists():
            return stock_count
        
        for quantity, product__unit in stocks:
            stock_count += convert_to_unit(quantity, product__unit, Product.MeasurementUnit.EA)

        return int(stock_count) or 0

# Location of the product in the warehouse, e.g. A1, B2, etc.
class Location(TimestampedModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="locations")
    code = models.CharField(max_length=32)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "location"
        unique_together = ("warehouse", "code")
        ordering = ["warehouse__name", "code"]

    def __str__(self):
        return f"{self.code} ({self.warehouse.name})"
