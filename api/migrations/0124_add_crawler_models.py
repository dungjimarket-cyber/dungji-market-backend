# Generated manually for crawler models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0123_fix_phone_shop_flows_v2'),
    ]

    operations = [
        migrations.CreateModel(
            name='CrawlSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crawler_type', models.CharField(choices=[('all', '전체'), ('lawyer', '변호사'), ('judicial_scrivener', '법무사'), ('tax_accountant', '세무사'), ('accountant', '공인회계사'), ('realtor', '공인중개사')], default='all', max_length=30, verbose_name='크롤러 유형')),
                ('status', models.CharField(choices=[('pending', '대기'), ('running', '실행 중'), ('completed', '완료'), ('failed', '실패')], default='pending', max_length=20, verbose_name='상태')),
                ('regions', models.JSONField(blank=True, default=list, verbose_name='검색 지역')),
                ('max_pages', models.IntegerField(default=5, verbose_name='최대 페이지')),
                ('total_count', models.IntegerField(default=0, verbose_name='총 수집')),
                ('email_count', models.IntegerField(default=0, verbose_name='이메일 수')),
                ('result_file', models.FileField(blank=True, null=True, upload_to='crawler_results/', verbose_name='결과 파일')),
                ('error_message', models.TextField(blank=True, verbose_name='오류 메시지')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='완료일')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='실행자')),
            ],
            options={
                'verbose_name': '크롤링 세션',
                'verbose_name_plural': '크롤링 세션',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CrawlResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('lawyer', '변호사'), ('judicial_scrivener', '법무사'), ('tax_accountant', '세무사'), ('accountant', '공인회계사'), ('realtor', '공인중개사')], max_length=30, verbose_name='업종')),
                ('name', models.CharField(blank=True, max_length=100, verbose_name='성명/대표자')),
                ('office_name', models.CharField(blank=True, max_length=200, verbose_name='사무소명')),
                ('affiliation', models.CharField(blank=True, max_length=200, verbose_name='소속')),
                ('address', models.TextField(blank=True, verbose_name='주소')),
                ('region', models.CharField(blank=True, max_length=50, verbose_name='지역')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='전화번호')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='이메일')),
                ('website', models.URLField(blank=True, verbose_name='홈페이지')),
                ('specialty', models.CharField(blank=True, max_length=200, verbose_name='전문분야')),
                ('extra_data', models.JSONField(blank=True, default=dict, verbose_name='추가 데이터')),
                ('email_sent', models.BooleanField(default=False, verbose_name='이메일 발송')),
                ('email_sent_at', models.DateTimeField(blank=True, null=True, verbose_name='발송일')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='수집일')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='api.crawlsession', verbose_name='세션')),
            ],
            options={
                'verbose_name': '크롤링 결과',
                'verbose_name_plural': '크롤링 결과',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='crawlresult',
            index=models.Index(fields=['category'], name='api_crawlre_categor_7e6e5d_idx'),
        ),
        migrations.AddIndex(
            model_name='crawlresult',
            index=models.Index(fields=['email'], name='api_crawlre_email_1dd7b3_idx'),
        ),
        migrations.AddIndex(
            model_name='crawlresult',
            index=models.Index(fields=['region'], name='api_crawlre_region_d7b1c6_idx'),
        ),
        migrations.AddIndex(
            model_name='crawlresult',
            index=models.Index(fields=['email_sent'], name='api_crawlre_email_s_e5b5a1_idx'),
        ),
        migrations.CreateModel(
            name='EmailCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='캠페인명')),
                ('subject', models.CharField(max_length=200, verbose_name='이메일 제목')),
                ('content', models.TextField(verbose_name='이메일 내용')),
                ('html_content', models.TextField(blank=True, verbose_name='HTML 내용')),
                ('target_categories', models.JSONField(default=list, verbose_name='대상 업종')),
                ('target_regions', models.JSONField(default=list, verbose_name='대상 지역')),
                ('status', models.CharField(choices=[('draft', '작성 중'), ('scheduled', '예약'), ('sending', '발송 중'), ('completed', '완료'), ('failed', '실패')], default='draft', max_length=20, verbose_name='상태')),
                ('total_count', models.IntegerField(default=0, verbose_name='총 발송')),
                ('success_count', models.IntegerField(default=0, verbose_name='성공')),
                ('fail_count', models.IntegerField(default=0, verbose_name='실패')),
                ('scheduled_at', models.DateTimeField(blank=True, null=True, verbose_name='예약 시간')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='시작 시간')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='완료 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='작성자')),
                ('target_results', models.ManyToManyField(blank=True, related_name='campaigns', to='api.crawlresult', verbose_name='발송 대상')),
            ],
            options={
                'verbose_name': '이메일 캠페인',
                'verbose_name_plural': '이메일 캠페인',
                'ordering': ['-created_at'],
            },
        ),
    ]
