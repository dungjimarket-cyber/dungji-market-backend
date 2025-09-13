# Generated manually for adding 'defective' battery status option
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0011_update_battery_status_labels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usedphone',
            name='battery_status',
            field=models.CharField(
                choices=[
                    ('excellent', '최상'),
                    ('good', '좋음'),
                    ('fair', '보통'),
                    ('poor', '나쁨'),
                    ('defective', '불량')
                ],
                default='good',
                max_length=20,
                verbose_name='배터리상태'
            ),
        ),
    ]