from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.db import IntegrityError

from catalog.models import Product
from warehouse.models import Warehouse

from accounts.models import Audit as AuditLog

from .models import InventoryTransaction, Stock, StockLedger
from .services import post_inventory_transaction
from faker import Faker


class InventoryModelTests(TestCase):
    def setUp(self):
        self.fake = Faker()
        self.user = get_user_model().objects.create_user(self.fake.user_name(), password=self.fake.password(length=8))
        self.jkt = Warehouse.objects.create(code="JKT", name="Jakarta", location="Cakung")
        self.sby = Warehouse.objects.create(code="SBY", name="Surabaya", location="Rungkut")
        self.product = Product.objects.create(name="Mineral Water", unit="EA")

    def _txn(self, **kwargs):
        data = {
            "transaction_type": InventoryTransaction.Type.IN,
            "warehouse": self.jkt,
            "product": self.product,
            "quantity": 10,
            "created_by": self.user,
        }
        data.update(kwargs)
        return InventoryTransaction.objects.create(**data)
    
    #* on the database level
    def test_cannot_create_negative_inventory(self):
        with self.assertRaises(IntegrityError):
            Stock.objects.create(
                product = self.product,
                warehouse = self.jkt,
                quantity = -2
            )
    
    #* on the logic level
    def test_cannot_post_negative_inventory(self):
        txn = self._txn(quantity=-2)
        with self.assertRaises(ValidationError):
            post_inventory_transaction(txn, self.user)

    def test_post_in_updates_stock_and_ledger(self):
        txn = self._txn(quantity=10)
        post_inventory_transaction(txn, self.user)
        stock = Stock.objects.get(product=self.product, warehouse=self.jkt)
        self.assertEqual(stock.quantity, 10)
        entry = StockLedger.objects.get()
        self.assertEqual(entry.quantity, 10)
        self.assertEqual(entry.balance_after, 10)

    def test_out_and_transfer(self):
        post_inventory_transaction(self._txn(quantity=10), self.user)
        out = self._txn(transaction_type=InventoryTransaction.Type.OUT, quantity=3)
        post_inventory_transaction(out, self.user)
        transfer = self._txn(
            transaction_type=InventoryTransaction.Type.TRANSFER,
            quantity=2,
            destination_warehouse=self.sby,
        )
        post_inventory_transaction(transfer, self.user)
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 5)
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.sby).quantity, 2)

    def test_ledger_is_immutable(self):
        post_inventory_transaction(self._txn(quantity=5), self.user)
        entry = StockLedger.objects.get()
        with self.assertRaises(ValidationError):
            entry.quantity = 99
            entry.save()
        with self.assertRaises(ValidationError):
            entry.delete()

    def test_cannot_overdraw(self):
        post_inventory_transaction(self._txn(quantity=2), self.user)
        out = self._txn(transaction_type=InventoryTransaction.Type.OUT, quantity=5)
        with self.assertRaises(ValidationError):
            post_inventory_transaction(out, self.user)

    def test_audit_cannot_be_edited(self):
        log = AuditLog.objects.create(user=self.user, action="TEST", description="hello")
        with self.assertRaises(ValidationError):
            log.description = "changed"
            log.save()
