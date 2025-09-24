# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_electronics', '0004_increase_max_price_to_100m'),
    ]

    operations = [
        migrations.AddField(
            model_name='usedelectronics',
            name='sold_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='판매완료일'),
        ),
        migrations.AddField(
            model_name='electronicstransaction',
            name='seller_completed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='판매자 완료 시간'),
        ),
        migrations.AddField(
            model_name='electronicstransaction',
            name='buyer_completed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='구매자 완료 시간'),
        ),
    ]