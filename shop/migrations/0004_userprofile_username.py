from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0003_merge_conflicts'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='username',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
    ]

