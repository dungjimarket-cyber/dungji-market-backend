# Generated manually - 전문가 프로필 및 상담 매칭 모델

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0117_update_carrier_logos'),
    ]

    operations = [
        # ExpertProfile 모델 생성
        migrations.CreateModel(
            name='ExpertProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('representative_name', models.CharField(max_length=100, verbose_name='대표자명')),
                ('is_business', models.BooleanField(default=False, verbose_name='사업자 여부')),
                ('business_name', models.CharField(blank=True, max_length=255, verbose_name='상호명')),
                ('business_number', models.CharField(blank=True, max_length=20, verbose_name='사업자등록번호')),
                ('business_license_image', models.URLField(blank=True, verbose_name='사업자등록증 이미지')),
                ('license_number', models.CharField(blank=True, max_length=50, verbose_name='자격번호')),
                ('license_image', models.URLField(blank=True, verbose_name='자격증 이미지')),
                ('contact_phone', models.CharField(max_length=20, verbose_name='연락처')),
                ('contact_email', models.EmailField(blank=True, max_length=254, verbose_name='이메일')),
                ('profile_image', models.URLField(blank=True, verbose_name='프로필 이미지')),
                ('tagline', models.CharField(blank=True, max_length=100, verbose_name='한줄 소개')),
                ('introduction', models.TextField(blank=True, verbose_name='상세 소개')),
                ('status', models.CharField(choices=[('pending', '승인대기'), ('verified', '승인됨'), ('rejected', '거절됨'), ('suspended', '정지')], default='verified', max_length=20, verbose_name='상태')),
                ('is_receiving_requests', models.BooleanField(default=True, verbose_name='상담 요청 수신 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experts', to='api.localbusinesscategory', verbose_name='업종')),
                ('regions', models.ManyToManyField(related_name='expert_profiles', to='api.region', verbose_name='활동 지역')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='expert_profile', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '전문가 프로필',
                'verbose_name_plural': '전문가 프로필 관리',
                'ordering': ['-created_at'],
            },
        ),
        # ConsultationMatch 모델 생성
        migrations.CreateModel(
            name='ConsultationMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '대기중'), ('replied', '답변함'), ('connected', '연결됨'), ('completed', '완료')], default='pending', max_length=20, verbose_name='상태')),
                ('expert_message', models.TextField(blank=True, verbose_name='전문가 메시지')),
                ('available_time', models.CharField(blank=True, max_length=200, verbose_name='상담 가능 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('replied_at', models.DateTimeField(blank=True, null=True, verbose_name='답변 시점')),
                ('connected_at', models.DateTimeField(blank=True, null=True, verbose_name='연결 시점')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='완료 시점')),
                ('consultation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='api.consultationrequest', verbose_name='상담 요청')),
                ('expert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='api.expertprofile', verbose_name='전문가')),
            ],
            options={
                'verbose_name': '상담 매칭',
                'verbose_name_plural': '상담 매칭 관리',
                'ordering': ['-created_at'],
            },
        ),
        # ConsultationMatch unique constraint 추가
        migrations.AddConstraint(
            model_name='consultationmatch',
            constraint=models.UniqueConstraint(fields=('consultation', 'expert'), name='unique_consultation_expert_match'),
        ),
    ]
