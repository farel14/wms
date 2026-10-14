from django.test import TestCase
from django.db import IntegrityError, transaction
from django.test import TestCase

from inventory.models import Product, Stock, Warehouse


#* Update timestamp
#* updated_at changes when the product is saved again
#* No stock records
#* on_hand returns 0
#* One stock record
#* on_hand returns its quantity
#* Multiple stock records
#* on_hand returns their summed quantity
#* Negative stock adjustment
#* Sum reflects the negative quantity, if your stock model permits it




class ProductModelTest(TestCase):
    def setUp(self):
        self.sku = "SKU-001"
        self.product = Product.objects.create(
            sku=self.sku,
            name="Rice",
            unit="kg",
            description="Premium rice",
        )
        
        #* Create a product, product is saved with the correct fields
    def test_create_product(self):
        """A product can be created with the expected fields."""
        self.assertEqual(self.product.sku, self.sku)
        self.assertEqual(self.product.name, "Rice")
        self.assertEqual(self.product.unit, "kg")
        self.assertEqual(self.product.description, "Premium rice")

        #* Default is_active
    def test_default_is_active(self):
        self.assertTrue(self.product.is_active)

    #* String representation "SKU-001 - Rice (kg)"
    def test_string_representation(self):
        self.assertEqual(
            str(self.product),
            "SKU-001 - Rice (kg)",
        )

    #* Duplicate SKU
    #* Database rejects duplicate SKUs
    def test_sku_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    sku=self.sku,
                    name="Another Rice",
                    unit="kg",
                )

    #* Creation timestamp, created_at is populated
    def test_created_at_is_populated(self):
        self.assertIsNotNone(self.product.created_at)

    #* No stock records, on_hand returns 0
    def test_on_hand_without_stock_returns_zero(self):
        self.assertEqual(self.product.on_hand, 0)
        
    #* Multiple stocks record, on_hand returns its quantity from multiple warehouses
    def test_on_hand_sums_multiple_stock_records(self):
        warehouse_jkt = Warehouse.objects.create(
            code="WH-1",
            name="Warehouse Jakarta-1",
            location="Jakarta"
        )
        warehouse_sby = Warehouse.objects.create(
            code="WH-2",
            name="Warehouse Surabaya-2",
            location="Surabaya"
        )
        Stock.objects.create(
            product=self.product,
            quantity=10,
            warehouse=warehouse_jkt
        )
        Stock.objects.create(
            product=self.product,
            quantity=25,
            warehouse=warehouse_sby
        )

        self.assertEqual(self.product.on_hand, 35)