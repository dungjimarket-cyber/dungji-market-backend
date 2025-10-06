# Generated manually to add missing fields to CustomNoShowReport

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0090_add_twa_app_fields_to_popup'),
    ]

    operations = [
        # Add last_edited_at field
        migrations.AddField(
            model_name='customnoshowreport',
            name='last_edited_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='마지막 수정 시간'),
        ),
        # Add noshow_buyers field
        migrations.AddField(
            model_name='customnoshowreport',
            name='noshow_buyers',
            field=models.JSONField(blank=True, default=list, verbose_name='노쇼 구매자 목록'),
        ),
    ]
