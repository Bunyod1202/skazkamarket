from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0006_order_contacts'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='image_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='product',
            name='image_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
    ]

