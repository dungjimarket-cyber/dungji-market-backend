from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0105_increase_url_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='localbusiness',
            name='website_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='웹사이트 URL'),
        ),
        migrations.AddField(
            model_name='localbusiness',
            name='opening_hours',
            field=models.JSONField(blank=True, help_text='요일별 영업시간 JSON', null=True, verbose_name='영업시간'),
        ),
        migrations.AddField(
            model_name='localbusiness',
            name='editorial_summary',
            field=models.TextField(blank=True, help_text='Google이 생성한 장소 요약', null=True, verbose_name='Google 요약'),
        ),
        migrations.AddField(
            model_name='localbusiness',
            name='business_status',
            field=models.CharField(default='OPERATIONAL', help_text='OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY', max_length=50, verbose_name='영업 상태'),
        ),
        migrations.AddField(
            model_name='localbusiness',
            name='last_review_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='최근 리뷰 시간'),
        ),
    ]
