# seed_demo.py
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Product
from inventory.models import InventoryTransaction
from inventory.services import post_inventory_transaction
from warehouse.models import Warehouse, Location
from faker import Faker

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = "Load demo products, warehouses, and opening stock."

    @transaction.atomic
    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@wms-toyland.local"},
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        operator, _ = User.objects.get_or_create(
            username="operator",
            defaults={"first_name": "Justin", "last_name": "Timberlake", "email": "justin.timberlake@wms-toyland.local", "is_staff": True},
        )
        operator.set_password("operator123")
        operator.save()
        
        # create additional operators
        for i in range(1, 6):
            first_name = fake.first_name()
            last_name = fake.last_name()
            add_operator, _ = User.objects.get_or_create(
                username=f"operator{i}",
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{first_name.lower()}.{last_name.lower()}@wms-toyland.local",
                    "is_staff": True,
                },
            )
            add_operator.set_password("operator123")
            add_operator.save()

        jkt, _ = Warehouse.objects.get_or_create(
            code="JKT-01",
            defaults={"name": "Jakarta Distribution Center", "location": "Cakung, Jakarta"},
        )
        sby, _ = Warehouse.objects.get_or_create(
            code="SBY-01",
            defaults={"name": "Surabaya Hub", "location": "Rungkut, Surabaya"},
        )
        
        wh_staff_jkt, _ = Group.objects.get_or_create(
            name="Warehouse Staff JKT"
        )
                
        wh_staff_sby, _ = Group.objects.get_or_create(
            name="Warehouse Staff SBY"
        )
        
        staff_member_jkt_username = ["operator", "operator1", "operator2"]
        staff_member_sby_username = ["operator2", "operator3"]
        
        staff_user_jkt = User.objects.filter(username__in=staff_member_jkt_username)
        wh_staff_jkt.user_set.add(*staff_user_jkt)
        
        staff_user_sby = User.objects.filter(username__in=staff_member_sby_username)
        wh_staff_sby.user_set.add(*staff_user_sby)
        
        location = [
            (jkt, "JKT-A1", "Location A1 in Jakarta"),
            (jkt, "JKT-A2", "Location A2 in Jakarta"),
            (sby, "SBY-A1", "Location A1 in Surabaya"),
            (sby, "SBY-A2", "Location A2 in Surabaya"),
            (sby, "SBY-A3", "Location A3 in Surabaya"),
        ]
        
        Location.objects.bulk_create(
            [Location(
                warehouse=warehouse, 
                code=code, 
                description=description
                ) for warehouse, code, description in location],
            ignore_conflicts=True,
        )
        
        catalog = [
            (jkt, "Cow plushie small", 1200, "EA"),
            (jkt, "Cow plushie small", 20, "PK"),
            (jkt, "Die cast Ferrari F80", 900, "EA"),
            (jkt, "Ninja figure 10cm", 140, "EA"),
            (jkt, "Squishi cube 2.5cm", 36, "CS"),
            (sby, "Collectible cards 1 box", 18, "PK"),
            (sby, "Classic Building Blocks", 22, "PLT"),
        ]
        
        # products = {}
        # Product.objects.bulk_create(
        #     [Product(name=name, unit=unit) for _, name, _, unit in catalog],
        #     ignore_conflicts=True,
        # )
        
        # for warehouse, name, qty, _ in catalog:
            # product = products[name]
        for warehouse, name, qty, unit in catalog:
            product, _ = Product.objects.get_or_create(name=name, unit=unit)
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
