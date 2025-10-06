# Generated manually to add missing fields to CustomPenalty

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0091_add_custom_noshow_missing_fields'),
    ]

    operations = [
        # Add custom_groupbuy field
        migrations.AddField(
            model_name='custompenalty',
            name='custom_groupbuy',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='penalties',
                to='api.customgroupbuy',
                verbose_name='관련 커스텀 공구'
            ),
        ),
        # Add participant field
        migrations.AddField(
            model_name='custompenalty',
            name='participant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='penalties',
                to='api.customparticipant',
                verbose_name='관련 참여 정보'
            ),
        ),
    ]
