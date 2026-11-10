from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalog.models import Product
from inventory.models import InventoryTransaction, Stock, StockLedger
from warehouse.models import Location, Warehouse

from .models import InboundLine, InboundReceipt, InboundShipment


class InboundReceiptTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="receiver", password="test-password")
        self.warehouse = Warehouse.objects.create(
            code="JKT", name="Jakarta", location="Cakung"
        )
        self.location = Location.objects.create(warehouse=self.warehouse, code="A1")
        self.product = Product.objects.create(name="Water")
        self.shipment = InboundShipment.objects.create(
            warehouse=self.warehouse,
            supplier_name="Fresh Drinks Co.",
            created_by=self.user,
        )
        self.line = InboundLine.objects.create(
            shipment=self.shipment,
            product=self.product,
            expected_qty=10,
        )

    def test_receiving_partial_deliveries_updates_stock_once_per_receipt(self):
        self.client.force_login(self.user)
        url = reverse(
            "inbound-receive-line",
            args=[self.shipment.pk, self.line.pk],
        )

        for quantity in (6, 4):
            response = self.client.post(
                url,
                {"quantity": quantity, "location": self.location.pk},
            )
            self.assertEqual(response.status_code, 302)

        self.line.refresh_from_db()
        self.shipment.refresh_from_db()
        stock = Stock.objects.get(product=self.product, warehouse=self.warehouse)
        receipts = InboundReceipt.objects.select_related("inventory_transaction")

        self.assertEqual(self.line.received_qty, 10)
        self.assertEqual(self.shipment.status, InboundShipment.Status.RECEIVING)
        self.assertEqual(stock.quantity, 10)
        self.assertEqual(receipts.count(), 2)
        self.assertEqual(
            list(receipts.values_list("inventory_transaction__transaction_type", flat=True)),
            [InventoryTransaction.Type.IN, InventoryTransaction.Type.IN],
        )
        self.assertEqual(
            list(receipts.values_list("inventory_transaction__status", flat=True)),
            [InventoryTransaction.Status.POSTED, InventoryTransaction.Status.POSTED],
        )
        self.assertEqual(
            list(StockLedger.objects.order_by("id").values_list("quantity", flat=True)),
            [6, 4],
        )

    def test_over_receipt_does_not_change_stock_or_received_quantity(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("inbound-receive-line", args=[self.shipment.pk, self.line.pk]),
            {"quantity": 11, "location": self.location.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.line.refresh_from_db()
        self.assertEqual(self.line.received_qty, 0)
        self.assertFalse(Stock.objects.exists())
        self.assertFalse(InventoryTransaction.objects.exists())
        self.assertFalse(StockLedger.objects.exists())

    def test_failed_inventory_post_rolls_back_the_receipt(self):
        self.client.force_login(self.user)
        self.warehouse.is_opname = True
        self.warehouse.save(update_fields=["is_opname"])

        response = self.client.post(
            reverse("inbound-receive-line", args=[self.shipment.pk, self.line.pk]),
            {"quantity": 5, "location": self.location.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.line.refresh_from_db()
        self.assertEqual(self.line.received_qty, 0)
        self.assertFalse(InboundReceipt.objects.exists())
        self.assertFalse(InventoryTransaction.objects.exists())
        self.assertFalse(Stock.objects.exists())
        self.assertFalse(StockLedger.objects.exists())
