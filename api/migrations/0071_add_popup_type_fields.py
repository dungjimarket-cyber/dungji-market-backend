# Generated migration for popup type fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0068_noshow_report_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='notice',
            name='popup_type',
            field=models.CharField(
                choices=[
                    ('text', '텍스트 팝업'),
                    ('image', '이미지 팝업'),
                    ('mixed', '텍스트 + 이미지')
                ],
                default='text',
                help_text='팝업 표시 형식',
                max_length=10,
                verbose_name='팝업 타입'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_link_target',
            field=models.CharField(
                choices=[
                    ('_self', '현재 창'),
                    ('_blank', '새 창')
                ],
                default='_blank',
                help_text='팝업 링크 클릭 시 열기 방식',
                max_length=10,
                verbose_name='링크 열기 방식'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_show_today_close',
            field=models.BooleanField(
                default=True,
                help_text='오늘 하루 보지 않기 옵션 표시 여부',
                verbose_name='오늘 하루 보지 않기 표시'
            ),
        ),
    ]