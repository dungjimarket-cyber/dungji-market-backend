# Generated manually 2025-09-23 11:18
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('used_electronics', '0003_add_missing_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usedelectronics',
            name='price',
            field=models.IntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1000),
                    django.core.validators.MaxValueValidator(100000000)
                ],
                verbose_name='판매가격'
            ),
        ),
        migrations.AlterField(
            model_name='usedelectronics',
            name='min_offer_price',
            field=models.IntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100000000)
                ],
                verbose_name='최소제안가격'
            ),
        ),
    ]