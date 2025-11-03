from django.db import migrations


class Migration(migrations.Migration):
    # This merge resolves parallel 0002 migrations: 0002_order_status and 0002_safe_add_missing_columns
    dependencies = [
        ('shop', '0002_order_status'),
        ('shop', '0002_safe_add_missing_columns'),
    ]

    operations = []

