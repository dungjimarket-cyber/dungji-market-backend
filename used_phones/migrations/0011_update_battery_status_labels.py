# Generated manually for battery status label changes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0010_add_completion_fields'),
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
                    ('unknown', '확인불가')
                ],
                default='unknown',
                max_length=20,
                verbose_name='배터리상태'
            ),
        ),
    ]