from django import forms

from catalog.models import Product
from warehouse.models import Warehouse

from .models import InventoryTransaction


class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ["transaction_type", "warehouse", "destination_warehouse", "product", "quantity", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = Warehouse.objects.all()
        self.fields["destination_warehouse"].queryset = Warehouse.objects.all()
        self.fields["destination_warehouse"].required = False
        self.fields["product"].queryset = Product.objects.all()
        self.fields["quantity"].help_text = "Use a positive number. For adjustments, negative reduces stock."

    def clean(self):
        cleaned = super().clean()
        txn_type = cleaned.get("transaction_type")
        warehouse = cleaned.get("warehouse")
        product = cleaned.get("product")
        quantity = cleaned.get("quantity")
        if not (txn_type and warehouse and product and quantity is not None):
            return cleaned
        InventoryTransaction(
            transaction_type=txn_type,
            warehouse=warehouse,
            destination_warehouse=cleaned.get("destination_warehouse"),
            product=product,
            quantity=quantity,
        ).clean()
        return cleaned
