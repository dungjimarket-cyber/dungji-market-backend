# Generated manually 2025-09-03
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0071_add_popup_type_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='noshowreport',
            name='is_cancelled',
            field=models.BooleanField(default=False, verbose_name='취소 여부'),
        ),
        migrations.AddField(
            model_name='noshowreport',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='취소 시간'),
        ),
        migrations.AddField(
            model_name='noshowreport',
            name='cancellation_reason',
            field=models.TextField(blank=True, verbose_name='취소 사유'),
        ),
    ]