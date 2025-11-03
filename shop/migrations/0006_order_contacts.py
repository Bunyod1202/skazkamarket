from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0005_add_sort_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='contact_whatsapp',
            field=models.CharField(max_length=64, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='contact_email',
            field=models.EmailField(max_length=254, blank=True, null=True),
        ),
    ]

