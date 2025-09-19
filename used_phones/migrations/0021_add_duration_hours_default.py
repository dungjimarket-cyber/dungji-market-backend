# Generated manually to add default value for duration_hours

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0020_update_penalty_duration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usedphonepenalty',
            name='duration_hours',
            field=models.IntegerField(
                default=24,
                verbose_name='패널티시간',
                help_text='시간 단위로 입력 (예: 24시간 = 1일, 168시간 = 7일)'
            ),
        ),
    ]