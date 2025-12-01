# Generated migration for region change tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0120_fix_realtor_flows'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='region_last_changed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='지역 마지막 변경일'),
        ),
    ]
