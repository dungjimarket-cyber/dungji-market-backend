# Generated manually for time-based deal feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0098_add_custom_groupbuy_notifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='customgroupbuy',
            name='deal_type',
            field=models.CharField(
                choices=[('participant_based', '인원 모집형'), ('time_based', '기간한정')],
                default='participant_based',
                help_text='인원 모집형 또는 기간한정',
                max_length=20,
                verbose_name='특가 유형'
            ),
        ),
        migrations.AddField(
            model_name='customgroupbuy',
            name='description_link_previews',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"url": "...", "title": "...", "image": "...", "description": "..."}, ...]',
                verbose_name='설명 내 링크 미리보기'
            ),
        ),
    ]
