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
    ]
