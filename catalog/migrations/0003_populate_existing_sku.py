from django.db import migrations


def generate_skus(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")

    for index, product in enumerate(
        Product.objects.order_by("id").iterator(),
        start=1,
    ):
        product.sku = f"SKU-{index:03d}"
        product.save(update_fields=["sku"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_product_created_at_product_description_and_more"),
    ]

    operations = [
        migrations.RunPython(
            generate_skus,
            migrations.RunPython.noop,
        ),
    ]