# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0115_fix_cleaning_moving_flows'),
    ]

    operations = [
        migrations.AddField(
            model_name='consultationrequest',
            name='consultation_type_text',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='상담 유형'
            ),
        ),
        migrations.AlterField(
            model_name='consultationrequest',
            name='consultation_type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='requests',
                to='api.consultationtype',
                verbose_name='상담 유형(레거시)'
            ),
        ),
    ]
