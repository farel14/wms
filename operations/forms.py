from django import forms

from catalog.models import Product

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
    location = forms.CharField(max_length=100, empty_value="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
    location = forms.CharField(max_length=100, empty_value="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)