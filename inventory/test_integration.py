from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Audit
from catalog.models import Product
from warehouse.models import Warehouse

from .models import InventoryTransaction, Stock, StockLedger


class InventoryViewIntegrationTests(TestCase):
    def setUp(self):
        self.jkt = Warehouse.objects.create(code="JKT", name="Jakarta", location="Cakung")
        self.sby = Warehouse.objects.create(code="SBY", name="Surabaya", location="Rungkut")
        self.product = Product.objects.create(name="Mineral Water", unit="EA")
        self._login_as_user()
        
    def _login_as_user(self):
        User = get_user_model()
        username, password="clerk", "secret123"
        self.user = User.objects.create_user(username, password=password)
        self.client.login(username=username, password=password)
        
    def _login_as_admin(self):
        User = get_user_model()
        username, password = "admin", "secret123"
        self.admin = User.objects.create_superuser(username, "admin@example.com", password)
        self.client.login(username=username, password=password)

    def _create_payload(self, **overrides):
        data = {
            "transaction_type": InventoryTransaction.Type.IN,
            "warehouse": self.jkt.pk,
            "destination_warehouse": "",
            "product": self.product.pk,
            "quantity": 10,
            "notes": "receiving",
        }
        data.update(overrides)
        return data

    def test_stock_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("stock-list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_create_and_post_in_updates_stock_and_ledger(self):
        response = self.client.post(reverse("transaction-create"), self._create_payload())
        self.assertEqual(response.status_code, 302)

        txn = InventoryTransaction.objects.get()
        self.assertEqual(txn.status, InventoryTransaction.Status.DRAFT)
        self.assertEqual(txn.created_by, self.user)
        self.assertTrue(
            Audit.objects.filter(
                action=Audit.Action.CREATE,
                table_name="InventoryTransaction",
                record_id=str(txn.pk),
            ).exists()
        )
        self.assertRedirects(response, reverse("transaction-detail", args=[txn.pk]))

        post_response = self.client.post(reverse("transaction-post", args=[txn.pk]))
        self.assertRedirects(post_response, reverse("transaction-detail", args=[txn.pk]))

        txn.refresh_from_db()
        self.assertEqual(txn.status, InventoryTransaction.Status.POSTED)
        self.assertEqual(
            Stock.objects.get(product=self.product, warehouse=self.jkt).quantity,
            10,
        )
        ledger = StockLedger.objects.get()
        self.assertEqual(ledger.quantity, 10)
        self.assertEqual(ledger.balance_after, 10)
        self.assertTrue(
            Audit.objects.filter(
                action=Audit.Action.POST,
                table_name="InventoryTransaction",
                record_id=str(txn.pk),
            ).exists()
        )

        stock_list = self.client.get(reverse("stock-list"))
        self.assertContains(stock_list, "Mineral Water")
        self.assertContains(stock_list, "JKT")

        second_post = self.client.post(reverse("transaction-post", args=[txn.pk]), follow=True)
        self.assertContains(second_post, "This transaction is already posted.")
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 10)
        self.assertEqual(StockLedger.objects.count(), 1)
        self.assertEqual(
            Audit.objects.filter(
                action=Audit.Action.POST,
                table_name="InventoryTransaction",
                record_id=str(txn.pk),
            ).count(),
            1,
        )

    def test_create_and_post_transfer_moves_stock(self):
        self.client.post(reverse("transaction-create"), self._create_payload(quantity=10))
        inbound = InventoryTransaction.objects.get()
        self.client.post(reverse("transaction-post", args=[inbound.pk]))

        response = self.client.post(
            reverse("transaction-create"),
            self._create_payload(
                transaction_type=InventoryTransaction.Type.TRANSFER,
                quantity=4,
                destination_warehouse=self.sby.pk,
                notes="to Surabaya",
            ),
        )
        self.assertEqual(response.status_code, 302)
        transfer = InventoryTransaction.objects.exclude(pk=inbound.pk).get()
        self.client.post(reverse("transaction-post", args=[transfer.pk]))

        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 6)
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.sby).quantity, 4)

    def test_cannot_create_transaction_during_opname(self):
        # during opname normal users are not allowed to create transaction 
        self.jkt.is_opname = True
        self.jkt.save(update_fields=["is_opname"])

        response = self.client.post(reverse("transaction-create"), self._create_payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot create transactions during stock opname.")
        self.assertFalse(InventoryTransaction.objects.exists())

    def test_create_transaction_during_opname_as_admin(self):
        # during opname only superusers are allowed to create transaction 
        self.jkt.is_opname = True
        self.jkt.save(update_fields=["is_opname"])

        self._login_as_admin()
        response = self.client.post(reverse("transaction-create"), self._create_payload())
        self.assertEqual(response.status_code, 302)

        txn = InventoryTransaction.objects.get()
        self.assertEqual(txn.status, InventoryTransaction.Status.DRAFT)
        self.assertEqual(txn.created_by, self.admin)
        self.assertTrue(
            Audit.objects.filter(
                action=Audit.Action.CREATE,
                table_name="InventoryTransaction",
                record_id=str(txn.pk),
            ).exists()
        )
        self.assertRedirects(response, reverse("transaction-detail", args=[txn.pk]))

