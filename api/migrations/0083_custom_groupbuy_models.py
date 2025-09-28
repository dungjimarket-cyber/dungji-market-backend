# Generated manually for custom groupbuy feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0082_fix_unified_review_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomGroupBuy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='제목')),
                ('description', models.TextField(verbose_name='설명')),
                ('type', models.CharField(choices=[('online', '온라인'), ('offline', '오프라인')], max_length=20, verbose_name='유형')),
                ('categories', models.JSONField(default=list, verbose_name='카테고리')),
                ('usage_guide', models.TextField(blank=True, help_text='사용기간, 시간 조건 등 이용 안내사항', null=True, verbose_name='이용안내')),
                ('original_price', models.PositiveIntegerField(verbose_name='정가')),
                ('discount_rate', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='할인율')),
                ('target_participants', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(10)], verbose_name='목표 인원')),
                ('current_participants', models.PositiveIntegerField(default=0, verbose_name='현재 인원')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('max_wait_hours', models.PositiveIntegerField(help_text='24~720시간 (1~30일)', validators=[django.core.validators.MinValueValidator(24), django.core.validators.MaxValueValidator(720)], verbose_name='최대 대기 시간(시간)')),
                ('expired_at', models.DateTimeField(verbose_name='만료 시간')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='완료일')),
                ('seller_decision_deadline', models.DateTimeField(blank=True, help_text='기간 만료 시 인원 미달인 경우 24시간', null=True, verbose_name='판매자 결정 기한')),
                ('discount_valid_days', models.PositiveIntegerField(blank=True, choices=[(3, '3일'), (7, '7일'), (14, '14일'), (30, '30일'), (60, '60일'), (90, '90일')], help_text='할인코드/링크 사용 가능 기간', null=True, verbose_name='할인 유효기간')),
                ('discount_valid_until', models.DateTimeField(blank=True, null=True, verbose_name='할인 만료일')),
                ('allow_partial_sale', models.BooleanField(default=False, help_text='기간 종료 시 인원 미달이어도 판매자가 최종 결정 가능', verbose_name='부분 판매 허용')),
                ('online_discount_type', models.CharField(blank=True, choices=[('link_only', '할인링크만 제공'), ('code_only', '할인코드만 제공'), ('both', '할인링크 + 할인코드')], help_text='온라인 공구인 경우만 설정', max_length=20, null=True, verbose_name='온라인 할인 제공 방식')),
                ('discount_url', models.TextField(blank=True, null=True, verbose_name='할인링크')),
                ('discount_codes', models.JSONField(blank=True, default=list, verbose_name='할인코드 목록')),
                ('location', models.CharField(blank=True, max_length=300, null=True, verbose_name='매장 위치')),
                ('location_detail', models.TextField(blank=True, null=True, verbose_name='위치 상세')),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True, validators=[django.core.validators.RegexValidator('^[\\d\\-\\(\\)\\s]+$', '숫자, 하이픈, 괄호, 공백만 입력 가능합니다.')], verbose_name='연락처')),
                ('meta_title', models.CharField(blank=True, max_length=300, null=True)),
                ('meta_image', models.TextField(blank=True, null=True)),
                ('meta_description', models.TextField(blank=True, null=True)),
                ('meta_price', models.PositiveIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('recruiting', '모집중'), ('pending_seller', '판매자 확정 대기'), ('completed', '선착순 마감'), ('cancelled', '취소'), ('expired', '기간만료')], default='recruiting', max_length=20, verbose_name='상태')),
                ('view_count', models.PositiveIntegerField(default=0, verbose_name='조회수')),
                ('favorite_count', models.PositiveIntegerField(default=0, verbose_name='찜 수')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_groupbuys', to=settings.AUTH_USER_MODEL, verbose_name='판매자')),
            ],
            options={
                'verbose_name': '커스텀 특가',
                'verbose_name_plural': '커스텀 특가 관리',
                'db_table': 'custom_groupbuy',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomGroupBuyImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_url', models.TextField(verbose_name='이미지 URL')),
                ('order_index', models.PositiveIntegerField(default=0, verbose_name='순서')),
                ('is_primary', models.BooleanField(default=False, verbose_name='대표 이미지')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('custom_groupbuy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='api.customgroupbuy', verbose_name='공구')),
            ],
            options={
                'verbose_name': '공구 이미지',
                'verbose_name_plural': '공구 이미지 관리',
                'db_table': 'custom_groupbuy_image',
                'ordering': ['order_index'],
            },
        ),
        migrations.CreateModel(
            name='CustomParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('participated_at', models.DateTimeField(auto_now_add=True, verbose_name='참여일')),
                ('participation_code', models.CharField(max_length=50, unique=True, verbose_name='참여 코드')),
                ('discount_code', models.CharField(blank=True, max_length=50, null=True, verbose_name='할인코드')),
                ('discount_url', models.TextField(blank=True, null=True, verbose_name='할인링크')),
                ('discount_used', models.BooleanField(default=False, verbose_name='사용 여부')),
                ('discount_used_at', models.DateTimeField(blank=True, null=True, verbose_name='사용일')),
                ('status', models.CharField(choices=[('confirmed', '확정'), ('cancelled', '취소')], default='confirmed', max_length=20, verbose_name='상태')),
                ('custom_groupbuy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='api.customgroupbuy', verbose_name='공구')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_participations', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_custom_discounts', to=settings.AUTH_USER_MODEL, verbose_name='검증자')),
            ],
            options={
                'verbose_name': '참여자',
                'verbose_name_plural': '참여자 관리',
                'db_table': 'custom_participant',
                'ordering': ['participated_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='찜한 날짜')),
                ('custom_groupbuy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='api.customgroupbuy', verbose_name='공구')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_favorites', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '찜',
                'verbose_name_plural': '찜 관리',
                'db_table': 'custom_favorite',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomGroupBuyRegion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('custom_groupbuy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='region_links', to='api.customgroupbuy', verbose_name='공구')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_groupbuy_regions', to='api.region', verbose_name='지역')),
            ],
            options={
                'verbose_name': '커스텀 공구 지역',
                'verbose_name_plural': '커스텀 공구 지역 관리',
                'db_table': 'custom_groupbuy_region',
                'ordering': ['region__code'],
            },
        ),
        migrations.AddIndex(
            model_name='customgroupbuy',
            index=models.Index(fields=['status'], name='custom_grou_status_idx'),
        ),
        migrations.AddIndex(
            model_name='customgroupbuy',
            index=models.Index(fields=['type'], name='custom_grou_type_idx'),
        ),
        migrations.AddIndex(
            model_name='customgroupbuy',
            index=models.Index(fields=['seller'], name='custom_grou_seller_idx'),
        ),
        migrations.AddIndex(
            model_name='customgroupbuy',
            index=models.Index(fields=['-created_at'], name='custom_grou_created_idx'),
        ),
        migrations.AddIndex(
            model_name='customgroupbuy',
            index=models.Index(fields=['expired_at'], name='idx_custom_expired'),
        ),
        migrations.AddIndex(
            model_name='customgroupbuy',
            index=models.Index(fields=['seller_decision_deadline'], name='idx_custom_seller_decision'),
        ),
        migrations.AlterUniqueTogether(
            name='customgroupbuyimage',
            unique_together={('custom_groupbuy', 'order_index')},
        ),
        migrations.AlterUniqueTogether(
            name='customparticipant',
            unique_together={('custom_groupbuy', 'user')},
        ),
        migrations.AlterUniqueTogether(
            name='customfavorite',
            unique_together={('user', 'custom_groupbuy')},
        ),
        migrations.AlterUniqueTogether(
            name='customgroupbuyregion',
            unique_together={('custom_groupbuy', 'region')},
        ),
    ]