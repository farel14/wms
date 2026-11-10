
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear database data and reseed demo data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Database connection to use.",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Skip the confirmation prompt.",
        )

    def handle(self, *args, **options):
        database = options["database"]

        self.stdout.write(
            self.style.WARNING(
                f"Clearing all data from database '{database}'..."
            )
        )

        call_command(
            "flush",
            database=database,
            interactive=not options["noinput"],
        )

        self.stdout.write("Running seed_demo...")
        call_command("seed_demo")

        self.stdout.write(
            self.style.SUCCESS("Database reset and demo seeding completed.")
        )
