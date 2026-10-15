
from django.test import TestCase
from faker import Faker
from catalog.forms import ProductForm

fake = Faker()

class ProductFormTest(TestCase):
    
    def test_form_with_valid_data(self):
        """The form should be valid when all required fields are correctly filled."""
        form_data = {
            "name": fake.word(),
            "unit": "pcs"  # Assuming 'pcs', 'kg', etc., are valid units
        }
        
        form = ProductForm(data=form_data)
        
        # Check if the validation passes
        self.assertTrue(form.is_valid())

    def test_form_is_invalid_without_name(self):
        """The form should fail validation if a required field like 'name' is missing."""
        form_data = {
            "name": "",  # Empty name
            "unit": "pcs"
        }
        
        form = ProductForm(data=form_data)
        
        # Check that the form validation fails
        self.assertFalse(form.is_valid())
        
        # Verify that the specific error message is attached to the 'name' field
        self.assertIn("name", form.errors)
        self.assertEqual(form.errors["name"][0], "This field is required.")

    def test_form_is_invalid_without_unit(self):
        """The form should fail validation if 'unit' is missing."""
        form_data = {
            "name": "Box Widget",
            "unit": ""  # Empty unit
        }
        
        form = ProductForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn("unit", form.errors)
