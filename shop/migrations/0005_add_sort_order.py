from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0004_userprofile_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
        migrations.AddField(
            model_name='product',
            name='sort_order',
            field=models.PositiveIntegerField(default=0, db_index=True),
        ),
    ]

