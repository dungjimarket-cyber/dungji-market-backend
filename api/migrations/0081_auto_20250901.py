# Generated manually on 2025-09-01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0080_auto_20250830_2257'),
    ]

    operations = [
        migrations.AddField(
            model_name='notice',
            name='show_in_main',
            field=models.BooleanField(default=False, help_text='메인 화면에 노출할지 여부', verbose_name='메인 화면 노출'),
        ),
        migrations.AddField(
            model_name='notice',
            name='display_type',
            field=models.CharField(choices=[('banner', '배너 이미지'), ('text', '텍스트 공지'), ('both', '배너 + 텍스트')], default='text', help_text='메인 화면 노출 방식', max_length=10, verbose_name='노출 방식'),
        ),
        migrations.AddField(
            model_name='notice',
            name='main_banner_image',
            field=models.ImageField(blank=True, help_text='메인 화면 배너 이미지 (권장: 1200x400)', null=True, upload_to='notices/banners/%Y/%m/', verbose_name='메인 배너 이미지'),
        ),
        migrations.AddField(
            model_name='notice',
            name='banner_link',
            field=models.URLField(blank=True, help_text='배너 클릭 시 이동할 URL (비워두면 공지사항 상세 페이지로 이동)', null=True, verbose_name='배너 클릭 링크'),
        ),
        migrations.AddField(
            model_name='notice',
            name='main_display_order',
            field=models.IntegerField(default=0, help_text='숫자가 작을수록 먼저 표시 (0이 가장 먼저)', verbose_name='메인 노출 순서'),
        ),
        migrations.AddIndex(
            model_name='notice',
            index=models.Index(fields=['show_in_main', 'main_display_order'], name='api_notice_show_in_9a3e5f_idx'),
        ),
    ]