from django import forms

from catalog.models import Product
from warehouse.models import Location

from .models import InboundLine, InboundShipment, OutboundLine, OutboundOrder


class InboundShipmentForm(forms.ModelForm):
    class Meta:
        model = InboundShipment
        fields = ["warehouse", "supplier_name", "expected_date", "notes"]
        widgets = {"expected_date": forms.DateInput(attrs={"type": "date"})}


class InboundLineForm(forms.ModelForm):
    class Meta:
        model = InboundLine
        fields = ["product", "expected_qty"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True)


class ReceiveLineForm(forms.Form):
    quantity = forms.IntegerField(min_value=1)
    location = forms.ModelChoiceField(queryset=Location.objects.none())

    def __init__(self, *args, warehouse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if warehouse:
            self.fields["location"].queryset = Location.objects.filter(warehouse=warehouse, is_active=True)


class OutboundOrderForm(forms.ModelForm):
    class Meta:
        model = OutboundOrder
        fields = ["warehouse", "customer_name", "required_date", "notes"]
        widgets = {"required_date": forms.DateInput(attrs={"type": "date"})}


class OutboundLineForm(forms.ModelForm):
    class Meta:
        model = OutboundLine
        fields = ["product", "requested_qty"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True)


class PickLineForm(forms.Form):
    quantity = forms.IntegerField(min_value=1)
    location = forms.ModelChoiceField(queryset=Location.objects.none())

    def __init__(self, *args, warehouse=None, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Location.objects.filter(is_active=True)
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        if product:
            qs = qs.filter(balances__product=product, balances__quantity__gt=0)
        self.fields["location"].queryset = qs.distinct()
