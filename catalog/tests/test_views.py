from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Audit
from catalog.models import Product


class ProductViewIntegrationTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user("clerk", password="secret123")
        self.client.login(username="clerk", password="secret123")

    def test_product_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("product-list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_create_product_via_http(self):
        response = self.client.post(
            reverse("product-create"),
            {"name": "Rice", "unit": "kg", "description": "Premium rice"},
        )
        self.assertEqual(response.status_code, 302)

        product = Product.objects.get()
        self.assertEqual(product.name, "Rice")
        self.assertTrue(product.sku.startswith("SKU-"))
        self.assertRedirects(response, reverse("product-detail", args=[product.pk]))
        self.assertTrue(
            Audit.objects.filter(
                action=Audit.Action.CREATE,
                table_name="Product",
                record_id=str(product.pk),
            ).exists()
        )

        detail = self.client.get(reverse("product-detail", args=[product.pk]))
        self.assertContains(detail, "Rice")

    def test_deactivate_and_activate_product(self):
        product = Product.objects.create(name="Tofu", unit="pcs")
        deactivate = self.client.post(reverse("product-deactivate", args=[product.pk]))
        self.assertRedirects(deactivate, reverse("product-detail", args=[product.pk]))
        product.refresh_from_db()
        self.assertFalse(product.is_active)

        activate = self.client.post(reverse("product-activate", args=[product.pk]))
        self.assertRedirects(activate, reverse("product-detail", args=[product.pk]))
        product.refresh_from_db()
        self.assertTrue(product.is_active)
