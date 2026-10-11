from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Product
from inventory.models import InventoryTransaction
from inventory.services import post_inventory_transaction
from warehouse.models import Warehouse

User = get_user_model()


class Command(BaseCommand):
    help = "Load demo products, warehouses, and opening stock."

    @transaction.atomic
    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@harbor-wms.local"},
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        operator, _ = User.objects.get_or_create(
            username="operator",
            defaults={"first_name": "Sari", "last_name": "Putri", "email": "sari@harbor-wms.local"},
        )
        operator.set_password("operator123")
        operator.save()

        jkt, _ = Warehouse.objects.get_or_create(
            code="JKT-01",
            defaults={"name": "Jakarta Distribution Center", "location": "Cakung, Jakarta"},
        )
        sby, _ = Warehouse.objects.get_or_create(
            code="SBY-01",
            defaults={"name": "Surabaya Hub", "location": "Rungkut, Surabaya"},
        )

        catalog = [
            ("Hex bolt M8 x 40mm", "EA"),
            ("Hex nut M8", "EA"),
            ("Medium carton", "EA"),
            ("Packing tape 48mm", "RL"),
            ("Safety helmet", "EA"),
            ("Nitrile glove large", "PR"),
        ]
        products = {}
        for name, unit in catalog:
            products[name], _ = Product.objects.get_or_create(name=name, defaults={"unit": unit})

        opening = [
            (jkt, "Hex bolt M8 x 40mm", 1200),
            (jkt, "Hex nut M8", 900),
            (jkt, "Medium carton", 140),
            (jkt, "Packing tape 48mm", 36),
            (sby, "Safety helmet", 18),
            (sby, "Nitrile glove large", 22),
        ]
        for warehouse, name, qty in opening:
            product = products[name]
            exists = InventoryTransaction.objects.filter(
                warehouse=warehouse,
                product=product,
                transaction_type=InventoryTransaction.Type.IN,
                notes="Demo opening balance",
            ).exists()
            if exists:
                continue
            txn = InventoryTransaction.objects.create(
                transaction_type=InventoryTransaction.Type.IN,
                warehouse=warehouse,
                product=product,
                quantity=qty,
                notes="Demo opening balance",
                created_by=admin,
            )
            post_inventory_transaction(txn, admin)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Login as admin / admin123 or operator / operator123")
