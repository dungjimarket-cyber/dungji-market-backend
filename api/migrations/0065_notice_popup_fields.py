# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0064_auto_20250901_notice_main_display'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notice',
            name='display_type',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('banner', '배너 이미지'),
                    ('text', '텍스트 공지'),
                    ('both', '배너 + 텍스트'),
                    ('popup', '팝업'),
                ],
                default='text',
                verbose_name='노출 방식',
                help_text='메인 화면 노출 방식'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_width',
            field=models.IntegerField(
                default=500,
                verbose_name='팝업 너비',
                help_text='팝업 창 너비 (픽셀)'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_height',
            field=models.IntegerField(
                default=600,
                verbose_name='팝업 높이',
                help_text='팝업 창 높이 (픽셀)'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_image',
            field=models.ImageField(
                upload_to='notices/popups/%Y/%m/',
                blank=True,
                null=True,
                verbose_name='팝업 이미지',
                help_text='팝업에 표시할 이미지'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_link',
            field=models.URLField(
                blank=True,
                null=True,
                verbose_name='팝업 클릭 링크',
                help_text='팝업 클릭 시 이동할 URL'
            ),
        ),
        migrations.AddField(
            model_name='notice',
            name='popup_expires_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name='팝업 종료일시',
                help_text='이 시간 이후에는 팝업이 자동으로 표시되지 않음'
            ),
        ),
    ]