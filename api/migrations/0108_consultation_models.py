# Generated manually for consultation feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0107_add_custom_photo_field'),
    ]

    operations = [
        # ConsultationType 모델 생성
        migrations.CreateModel(
            name='ConsultationType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='상담 유형명')),
                ('description', models.TextField(blank=True, verbose_name='설명')),
                ('icon', models.CharField(default='💬', max_length=10, verbose_name='아이콘')),
                ('order_index', models.IntegerField(default=0, verbose_name='정렬순서')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consultation_types',
                    to='api.localbusinesscategory',
                    verbose_name='업종'
                )),
            ],
            options={
                'verbose_name': '상담 유형',
                'verbose_name_plural': '상담 유형',
                'db_table': 'api_consultation_type',
                'ordering': ['category', 'order_index'],
            },
        ),
        # ConsultationRequest 모델 생성
        migrations.CreateModel(
            name='ConsultationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='이름')),
                ('phone', models.CharField(max_length=20, verbose_name='연락처')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='이메일')),
                ('region', models.CharField(max_length=50, verbose_name='희망 지역')),
                ('content', models.TextField(verbose_name='상담 내용')),
                ('ai_summary', models.TextField(blank=True, verbose_name='AI 정리 내용')),
                ('ai_recommended_types', models.JSONField(blank=True, default=list, verbose_name='AI 추천 상담 유형')),
                ('status', models.CharField(
                    choices=[
                        ('pending', '대기중'),
                        ('contacted', '연락완료'),
                        ('completed', '상담완료'),
                        ('cancelled', '취소')
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='상태'
                )),
                ('admin_note', models.TextField(blank=True, verbose_name='관리자 메모')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='신청일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('contacted_at', models.DateTimeField(blank=True, null=True, verbose_name='연락일시')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='완료일시')),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='consultation_requests',
                    to='api.localbusinesscategory',
                    verbose_name='업종'
                )),
                ('consultation_type', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='requests',
                    to='api.consultationtype',
                    verbose_name='상담 유형'
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='consultation_requests',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='회원'
                )),
            ],
            options={
                'verbose_name': '상담 신청',
                'verbose_name_plural': '상담 신청',
                'db_table': 'api_consultation_request',
                'ordering': ['-created_at'],
            },
        ),
    ]
