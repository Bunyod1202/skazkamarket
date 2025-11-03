from django.db import migrations


def safe_add_columns(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()

    def col_exists_pg(table, col):
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name=%s AND column_name=%s
            """,
            [table, col],
        )
        return cursor.fetchone() is not None

    def col_exists_sqlite(table, col):
        cursor.execute(f"PRAGMA table_info('{table}')")
        return any(r[1] == col for r in cursor.fetchall())

    if vendor == 'postgresql':
        # shop_category.name_en
        if not col_exists_pg('shop_category', 'name_en'):
            cursor.execute("ALTER TABLE shop_category ADD COLUMN name_en varchar(255) DEFAULT '' NOT NULL;")
        # shop_category.image
        if not col_exists_pg('shop_category', 'image'):
            cursor.execute("ALTER TABLE shop_category ADD COLUMN image varchar(100);")
        # shop_product.name_en
        if not col_exists_pg('shop_product', 'name_en'):
            cursor.execute("ALTER TABLE shop_product ADD COLUMN name_en varchar(255) DEFAULT '' NOT NULL;")
        # shop_order.status
        if not col_exists_pg('shop_order', 'status'):
            cursor.execute("ALTER TABLE shop_order ADD COLUMN status varchar(16) DEFAULT 'new' NOT NULL;")
    else:
        # SQLite or others – attempt best-effort
        # shop_category.name_en
        if not col_exists_sqlite('shop_category', 'name_en'):
            cursor.execute("ALTER TABLE shop_category ADD COLUMN name_en TEXT DEFAULT '';")
        # shop_category.image
        if not col_exists_sqlite('shop_category', 'image'):
            cursor.execute("ALTER TABLE shop_category ADD COLUMN image TEXT;")
        # shop_product.name_en
        if not col_exists_sqlite('shop_product', 'name_en'):
            cursor.execute("ALTER TABLE shop_product ADD COLUMN name_en TEXT DEFAULT '';")
        # shop_order.status
        if not col_exists_sqlite('shop_order', 'status'):
            cursor.execute("ALTER TABLE shop_order ADD COLUMN status TEXT DEFAULT 'new';")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(safe_add_columns, reverse_code=noop),
    ]

