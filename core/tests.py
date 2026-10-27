from django.test import TestCase
from catalog.models import Product

# Create your tests here.

class ActiveQuerySetTestCase(TestCase):
    
    def setUp(self):
        self.active_product_1 = Product.objects.create(
            name="Water Gun",
            unit=Product.MeasurementUnit.EA,
            description="High capacity watergun",
            is_active=True
        )
        self.active_product_2 = Product.objects.create(
            name="Glitter Bomb",
            unit=Product.MeasurementUnit.PK,
            description="Prank glitter bomb for fun",
            # is_active=True by default
        )
        self.inactive_product_1 = Product.objects.create(
            name="Fake corn",
            unit=Product.MeasurementUnit.EA,
            description="The fakest corn ever exist",
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


    