from django.db import models
from django.db.models import Sum


class Product(models.Model):
    name = models.CharField(max_length=160, unique=True)
    unit = models.CharField(max_length=16)

    class Meta:
        db_table = "product"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.unit})"

    @property
    def on_hand(self):
        return self.stocks.aggregate(total=Sum("quantity"))["total"] or 0
