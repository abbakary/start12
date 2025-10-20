from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Update Customer unique constraint to be branch-scoped (branch, full_name, phone, organization_name, tax_number)."

    def handle(self, *args, **options):
        table = "tracker_customer"
        index_name = "uniq_customer_identity"
        new_columns = ["branch_id", "full_name", "phone", "organization_name", "tax_number"]

        self.stdout.write("Checking existing index...")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s", [index_name])
                rows = cursor.fetchall()

                if rows:
                    self.stdout.write(f"Dropping existing index `{index_name}` ...")
                    cursor.execute(f"ALTER TABLE `{table}` DROP INDEX `{index_name}`")
                else:
                    self.stdout.write("Existing index not found; proceeding to create new one.")

                cols_sql = ", ".join(f"`{c}`" for c in new_columns)
                self.stdout.write(
                    f"Creating unique index `{index_name}` on columns: {', '.join(new_columns)} ..."
                )
                cursor.execute(
                    f"CREATE UNIQUE INDEX `{index_name}` ON `{table}` ({cols_sql})"
                )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to update unique constraint: {e}"))
            raise

        self.stdout.write(self.style.SUCCESS("Customer unique constraint updated successfully."))
