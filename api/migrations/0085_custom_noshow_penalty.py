# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0084_update_custom_groupbuy_pricing'),
    ]

    operations = [
        # CustomNoShowReport 모델 생성
        migrations.CreateModel(
            name='CustomNoShowReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type', models.CharField(choices=[('seller_noshow', '판매자 노쇼'), ('buyer_noshow', '구매자 노쇼')], max_length=20, verbose_name='신고 유형')),
                ('content', models.TextField(verbose_name='신고 내용')),
                ('evidence_image', models.ImageField(blank=True, null=True, upload_to='custom_noshow_reports/', verbose_name='증빙 이미지 1')),
                ('evidence_image_2', models.ImageField(blank=True, null=True, upload_to='custom_noshow_reports/', verbose_name='증빙 이미지 2')),
                ('evidence_image_3', models.ImageField(blank=True, null=True, upload_to='custom_noshow_reports/', verbose_name='증빙 이미지 3')),
                ('status', models.CharField(choices=[('pending', '처리중'), ('completed', '처리완료'), ('rejected', '반려')], default='pending', max_length=20, verbose_name='처리 상태')),
                ('admin_comment', models.TextField(blank=True, null=True, verbose_name='관리자 코멘트')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='신고 일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정 일시')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='처리 일시')),
                ('edit_count', models.PositiveIntegerField(default=0, verbose_name='수정 횟수')),
                ('is_cancelled', models.BooleanField(default=False, verbose_name='취소 여부')),
                ('cancelled_at', models.DateTimeField(blank=True, null=True, verbose_name='취소 일시')),
                ('cancellation_reason', models.TextField(blank=True, null=True, verbose_name='취소 사유')),
                ('custom_groupbuy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='noshow_reports', to='api.customgroupbuy', verbose_name='커스텀 공구')),
                ('participant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='noshow_reports', to='api.customparticipant', verbose_name='참여 정보')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_custom_noshow_reports', to=settings.AUTH_USER_MODEL, verbose_name='처리자')),
                ('reported_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_noshow_reports_received', to=settings.AUTH_USER_MODEL, verbose_name='피신고자')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_noshow_reports_made', to=settings.AUTH_USER_MODEL, verbose_name='신고자')),
            ],
            options={
                'verbose_name': '커스텀 공구 노쇼 신고',
                'verbose_name_plural': '커스텀 공구 노쇼 신고',
                'db_table': 'custom_noshow_reports',
                'ordering': ['-created_at'],
            },
        ),
        # CustomPenalty 모델 생성
        migrations.CreateModel(
            name='CustomPenalty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(verbose_name='사유')),
                ('penalty_type', models.CharField(max_length=20, verbose_name='페널티 유형')),
                ('duration_hours', models.PositiveIntegerField(default=24, verbose_name='패널티 기간(시간)')),
                ('start_date', models.DateTimeField(auto_now_add=True, verbose_name='시작일')),
                ('end_date', models.DateTimeField(verbose_name='종료일')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성 여부')),
                ('count', models.PositiveIntegerField(default=1, verbose_name='누적 횟수')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='custom_penalties_created', to=settings.AUTH_USER_MODEL, verbose_name='생성자')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_penalties', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '커스텀 공구 패널티',
                'verbose_name_plural': '커스텀 공구 패널티',
                'db_table': 'custom_penalties',
                'ordering': ['-created_at'],
            },
        ),
    ]