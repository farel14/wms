from django.contrib import admin

from .models import InboundLine, InboundShipment, OutboundLine, OutboundOrder


class InboundLineInline(admin.TabularInline):
    model = InboundLine
    extra = 0


@admin.register(InboundShipment)
class InboundShipmentAdmin(admin.ModelAdmin):
    list_display = ("number", "warehouse", "supplier_name", "status", "expected_date", "created_at")
    list_filter = ("status", "warehouse")
    inlines = [InboundLineInline]


class OutboundLineInline(admin.TabularInline):
    model = OutboundLine
    extra = 0


@admin.register(OutboundOrder)
class OutboundOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "warehouse", "customer_name", "status", "required_date", "created_at")
    list_filter = ("status", "warehouse")
    inlines = [OutboundLineInline]
