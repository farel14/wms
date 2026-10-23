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
