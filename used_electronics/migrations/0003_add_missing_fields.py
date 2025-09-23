# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_electronics', '0002_remove_electronicsfavorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='usedelectronics',
            name='has_manual',
            field=models.BooleanField(default=False, verbose_name='매뉴얼포함'),
        ),
        migrations.AddField(
            model_name='usedelectronics',
            name='usage_period',
            field=models.CharField(blank=True, max_length=50, verbose_name='사용기간'),
        ),
        migrations.AddField(
            model_name='usedelectronics',
            name='is_unused',
            field=models.BooleanField(default=False, verbose_name='미개봉'),
        ),
    ]