# Generated manually for local business models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0101_add_discount_url_clicks_to_custom_groupbuy'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocalBusinessCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='업종명')),
                ('name_en', models.CharField(max_length=50, verbose_name='영문명', help_text='Google Places 검색용')),
                ('icon', models.CharField(default='🏢', max_length=50, verbose_name='아이콘')),
                ('google_place_type', models.CharField(max_length=100, verbose_name='Google Place Type', help_text='예: lawyer, accounting, real_estate_agency')),
                ('description', models.TextField(blank=True, verbose_name='설명')),
                ('order_index', models.IntegerField(default=0, verbose_name='정렬순서')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '지역업체 카테고리',
                'verbose_name_plural': '지역업체 카테고리',
                'db_table': 'local_business_category',
                'ordering': ['order_index', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LocalBusiness',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='업체명')),
                ('address', models.CharField(max_length=300, verbose_name='주소')),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True, verbose_name='전화번호')),
                ('google_place_id', models.CharField(max_length=200, unique=True, verbose_name='Google Place ID')),
                ('latitude', models.DecimalField(decimal_places=7, max_digits=10, verbose_name='위도')),
                ('longitude', models.DecimalField(decimal_places=7, max_digits=10, verbose_name='경도')),
                ('rating', models.DecimalField(blank=True, decimal_places=1, max_digits=2, null=True, verbose_name='평점')),
                ('review_count', models.IntegerField(default=0, verbose_name='리뷰 수')),
                ('google_maps_url', models.URLField(blank=True, max_length=500, verbose_name='구글 지도 URL')),
                ('photo_url', models.URLField(blank=True, max_length=500, null=True, verbose_name='대표 사진 URL')),
                ('popularity_score', models.FloatField(default=0, verbose_name='인기도 점수', help_text='베이지안 평균 기반')),
                ('rank_in_region', models.IntegerField(default=999, verbose_name='지역 내 순위', help_text='해당 지역+카테고리 내 순위 (1~5)')),
                ('is_verified', models.BooleanField(default=False, verbose_name='업체 인증', help_text='업체에서 직접 인증한 경우')),
                ('is_new', models.BooleanField(default=False, verbose_name='신규 업체', help_text='리뷰 10개 이하 또는 최근 등록')),
                ('view_count', models.PositiveIntegerField(default=0, verbose_name='조회수')),
                ('last_synced_at', models.DateTimeField(blank=True, null=True, verbose_name='마지막 동기화 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='businesses', to='api.localbusinesscategory', verbose_name='업종')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='local_businesses', to='api.region', verbose_name='지역')),
            ],
            options={
                'verbose_name': '지역 업체',
                'verbose_name_plural': '지역 업체',
                'db_table': 'local_business',
                'ordering': ['region', 'category', 'rank_in_region'],
            },
        ),
        migrations.CreateModel(
            name='LocalBusinessLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link_type', models.CharField(choices=[('news', '뉴스'), ('blog', '블로그'), ('review', '리뷰'), ('community', '커뮤니티')], max_length=20, verbose_name='링크 유형')),
                ('title', models.CharField(max_length=300, verbose_name='제목')),
                ('url', models.URLField(max_length=1000, unique=True, verbose_name='URL')),
                ('source', models.CharField(max_length=50, verbose_name='출처', help_text='네이버, 구글, 다음 등')),
                ('published_at', models.DateField(blank=True, null=True, verbose_name='작성일')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='links', to='api.localbusiness', verbose_name='업체')),
            ],
            options={
                'verbose_name': '업체 외부 링크',
                'verbose_name_plural': '업체 외부 링크',
                'db_table': 'local_business_link',
                'ordering': ['-published_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LocalBusinessView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(verbose_name='IP 주소')),
                ('viewed_at', models.DateTimeField(auto_now_add=True, verbose_name='조회 시간')),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='view_logs', to='api.localbusiness', verbose_name='업체')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '업체 조회 기록',
                'verbose_name_plural': '업체 조회 기록',
                'db_table': 'local_business_view',
            },
        ),
        migrations.AddIndex(
            model_name='localbusiness',
            index=models.Index(fields=['region', 'category', 'rank_in_region'], name='local_busin_region__b2e1f4_idx'),
        ),
        migrations.AddIndex(
            model_name='localbusiness',
            index=models.Index(fields=['google_place_id'], name='local_busin_google__3f8a5c_idx'),
        ),
        migrations.AddIndex(
            model_name='localbusiness',
            index=models.Index(fields=['is_new', '-created_at'], name='local_busin_is_new_c7b8d9_idx'),
        ),
        migrations.AddIndex(
            model_name='localbusiness',
            index=models.Index(fields=['-popularity_score'], name='local_busin_popular_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='localbusinesslink',
            index=models.Index(fields=['business', '-published_at'], name='local_busin_busines_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='localbusinessview',
            index=models.Index(fields=['business', '-viewed_at'], name='local_busin_busines_e7f8g9_idx'),
        ),
        migrations.AddIndex(
            model_name='localbusinessview',
            index=models.Index(fields=['-viewed_at'], name='local_busin_viewed__h0i1j2_idx'),
        ),
    ]
