# Generated manually for bump feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0094_add_sms_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='customgroupbuy',
            name='last_bumped_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='마지막 끌올 시간'),
        ),
        migrations.AddField(
            model_name='customgroupbuy',
            name='bump_count',
            field=models.PositiveIntegerField(default=0, verbose_name='총 끌올 횟수'),
        ),
        migrations.AlterField(
            model_name='unifiedbump',
            name='item_type',
            field=models.CharField(
                choices=[('phone', '휴대폰'), ('electronics', '전자제품'), ('custom_groupbuy', '커스텀공구')],
                max_length=20,
                verbose_name='상품타입'
            ),
        ),
    ]
