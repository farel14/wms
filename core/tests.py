from django.test import TestCase
# from django.contrib.auth.models import User
# from .models import Audit, log_audit
from .constants import MeasurementUnit
from catalog.models import Product
from faker import Faker

# Create your tests here.

class ConstantTestCase(TestCase):
    
    def test_unit_ea(self):
        self.assertEqual(MeasurementUnit.EA.symbol, "ea")
        self.assertEqual(MeasurementUnit.EA.label, "Each")
        self.assertEqual(MeasurementUnit.EA.to_each, 1.0)

    def test_convert(self):
        self.assertEqual(MeasurementUnit.PK.to_each * 2, MeasurementUnit.PK.convert_to(2, MeasurementUnit.EA))
        
class ActiveQuerySetTestCase(TestCase):
    
    def setUp(self):
        fake = Faker()
        self.active_product_1 = Product.objects.create(
            name="Rice",
            unit="kg",
            description="Premium rice",
            is_active=True
        )
        self.active_product_2 = Product.objects.create(
            name="Tofu",
            unit="pcs",
            description="Low quality tofu",
            # is_active=True by default
        )
        self.inactive_product_1 = Product.objects.create(
            name="Corn",
            unit="cobs",
            description="Corniest corn ever exist",
            is_active=False
        )

    def test_active_query(self):
        active_products = Product.objects.active()
        
        self.assertEqual(active_products.count(), 2)
        self.assertIn(self.active_product_1, active_products)
        self.assertIn(self.active_product_2, active_products)
        self.assertNotIn(self.inactive_product_1, active_products)

    
    def test_inactive_query(self):
        inactive_products = Product.objects.inactive()
        
        self.assertEqual(inactive_products.count(), 1)
        self.assertIn(self.inactive_product_1, inactive_products)
        self.assertNotIn(self.active_product_1, inactive_products)
        self.assertNotIn(self.active_product_2, inactive_products)


    