from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Audit
from warehouse.models import Warehouse


class WarehouseViewIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("clerk", password="secret123")
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "secret123")
        self.client.login(username="clerk", password="secret123")

    def test_warehouse_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("warehouse-list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_create_warehouse_via_http(self):
        response = self.client.post(
            reverse("warehouse-create"),
            {"code": "JKT", "name": "Jakarta", "location": "Cakung"},
        )
        self.assertEqual(response.status_code, 302)

        warehouse = Warehouse.objects.get()
        self.assertEqual(warehouse.code, "JKT")
        self.assertFalse(warehouse.is_opname)
        self.assertRedirects(response, reverse("warehouse-detail", args=[warehouse.pk]))
        self.assertTrue(
            Audit.objects.filter(
                action=Audit.Action.CREATE,
                table_name="Warehouse",
                record_id=str(warehouse.pk),
            ).exists()
        )

    def test_lock_opname_requires_superuser(self):
        warehouse = Warehouse.objects.create(code="SBY", name="Surabaya", location="Rungkut")
        forbidden = self.client.post(reverse("warehouse-lock-opname", args=[warehouse.pk]))
        self.assertEqual(forbidden.status_code, 403)
        warehouse.refresh_from_db()
        self.assertFalse(warehouse.is_opname)

        self.client.logout()
        self.client.login(username="admin", password="secret123")
        allowed = self.client.post(reverse("warehouse-lock-opname", args=[warehouse.pk]))
        self.assertRedirects(allowed, reverse("warehouse-list"))
        warehouse.refresh_from_db()
        self.assertTrue(warehouse.is_opname)
        self.assertTrue(
            Audit.objects.filter(
                action=Audit.Action.LOCK_OPNAME,
                table_name="Warehouse",
                record_id=str(warehouse.pk),
            ).exists()
        )
