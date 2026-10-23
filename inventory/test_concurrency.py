import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import OperationalError, close_old_connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from catalog.models import Product
from warehouse.models import Warehouse

from .models import InventoryTransaction, Stock, StockLedger
from .services import post_inventory_transaction


class InventoryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("clerk", password="secret123")
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

    def _run_concurrent(self, fns, timeout=15):
        barrier = threading.Barrier(len(fns), timeout=timeout)
        results = [None] * len(fns)
        errors = [None] * len(fns)

        def wrapper(index, fn):
            close_old_connections()
            try:
                barrier.wait(timeout=timeout)
                results[index] = fn()
            except Exception as exc:
                errors[index] = exc
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(fns)) as pool:
            futures = [pool.submit(wrapper, i, fn) for i, fn in enumerate(fns)]
            for future in as_completed(futures, timeout=timeout):
                future.result(timeout=timeout)
        return results, errors

    def test_reposting_the_same_transaction_is_idempotent(self):
        txn = self._txn(quantity=10)
        post_inventory_transaction(txn, self.user)

        with self.assertRaisesMessage(ValidationError, "This transaction is already posted."):
            post_inventory_transaction(txn, self.user)

        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 10)
        self.assertEqual(StockLedger.objects.filter(inventory_transaction=txn).count(), 1)

    def test_concurrent_posts_of_the_same_transaction_apply_once(self):
        txn = self._txn(quantity=7)
        txn_id = txn.pk
        user_id = self.user.pk

        def post_once():
            return post_inventory_transaction(
                InventoryTransaction.objects.get(pk=txn_id),
                get_user_model().objects.get(pk=user_id),
            )

        results, errors = self._run_concurrent([post_once, post_once])
        successes = [result for result in results if result is not None]
        failures = [error for error in errors if error is not None]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], ValidationError)
        self.assertIn("already posted", str(failures[0]))
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 7)
        self.assertEqual(StockLedger.objects.count(), 1)

    def test_concurrent_http_posts_of_the_same_transaction_apply_once(self):
        txn = self._txn(quantity=5)
        txn_id = txn.pk

        def post_http():
            client = Client()
            self.assertTrue(client.login(username="clerk", password="secret123"))
            return client.post(reverse("transaction-post", args=[txn_id]))

        results, errors = self._run_concurrent([post_http, post_http])
        self.assertTrue(all(error is None for error in errors))
        self.assertTrue(all(result.status_code == 302 for result in results))
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 5)
        self.assertEqual(StockLedger.objects.count(), 1)
        txn.refresh_from_db()
        self.assertEqual(txn.status, InventoryTransaction.Status.POSTED)

    def test_concurrent_inbound_transactions_sum_stock(self):
        first = self._txn(quantity=4)
        second = self._txn(quantity=6)

        def post(txn_id):
            return post_inventory_transaction(
                InventoryTransaction.objects.get(pk=txn_id),
                get_user_model().objects.get(pk=self.user.pk),
            )

        results, errors = self._run_concurrent(
            [lambda: post(first.pk), lambda: post(second.pk)]
        )
        self.assertTrue(all(error is None for error in errors))
        self.assertEqual(len([result for result in results if result is not None]), 2)
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 10)
        self.assertEqual(StockLedger.objects.count(), 2)

    def test_concurrent_overdraw_does_not_go_negative(self):
        seed = self._txn(quantity=10)
        post_inventory_transaction(seed, self.user)
        first_out = self._txn(transaction_type=InventoryTransaction.Type.OUT, quantity=8)
        second_out = self._txn(transaction_type=InventoryTransaction.Type.OUT, quantity=8)

        def post(txn_id):
            return post_inventory_transaction(
                InventoryTransaction.objects.get(pk=txn_id),
                get_user_model().objects.get(pk=self.user.pk),
            )

        results, errors = self._run_concurrent(
            [lambda: post(first_out.pk), lambda: post(second_out.pk)]
        )
        successes = [result for result in results if result is not None]
        failures = [error for error in errors if error is not None]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertIsInstance(failures[0], ValidationError)
        self.assertIn("Insufficient stock", str(failures[0]))
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 2)
        self.assertGreaterEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 0)

    def test_crossing_transfers_do_not_deadlock(self):
        """Opposite transfers lock the same stock rows in reverse order unless ordered by pk.

        PostgreSQL would then raise OperationalError ('deadlock detected') and abort one
        transaction. Locking both stock rows by (product, warehouse) pk first makes this
        deterministic instead of relying on deadlock detection.
        """
        Stock.objects.create(product=self.product, warehouse=self.jkt, quantity=10)
        Stock.objects.create(product=self.product, warehouse=self.sby, quantity=10)
        jkt_to_sby = self._txn(
            transaction_type=InventoryTransaction.Type.TRANSFER,
            quantity=3,
            destination_warehouse=self.sby,
        )
        sby_to_jkt = self._txn(
            transaction_type=InventoryTransaction.Type.TRANSFER,
            warehouse=self.sby,
            destination_warehouse=self.jkt,
            quantity=4,
        )

        def post(txn_id):
            try:
                return post_inventory_transaction(
                    InventoryTransaction.objects.get(pk=txn_id),
                    get_user_model().objects.get(pk=self.user.pk),
                )
            except OperationalError as exc:
                self.fail(f"Deadlock detected while posting transfers: {exc}")

        results, errors = self._run_concurrent(
            [lambda: post(jkt_to_sby.pk), lambda: post(sby_to_jkt.pk)],
            timeout=10,
        )
        self.assertTrue(all(error is None for error in errors), errors)
        self.assertEqual(len([result for result in results if result is not None]), 2)
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.jkt).quantity, 11)
        self.assertEqual(Stock.objects.get(product=self.product, warehouse=self.sby).quantity, 9)
