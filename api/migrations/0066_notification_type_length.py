# Generated manually to fix notification_type field length

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0065_notice_popup_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('reminder', '리마인더'),
                    ('success', '성공/최종선정'),
                    ('failure', '실패/취소'),
                    ('info', '정보/상태변경'),
                ],
                default='info'
            ),
        ),
    ]