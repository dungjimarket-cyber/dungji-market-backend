# Generated manually for review and report system
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_phones', '0013_fix_offer_counts'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsedPhoneReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_type', models.CharField(choices=[('fake_listing', '허위매물'), ('fraud', '사기'), ('abusive_language', '욕설'), ('inappropriate_behavior', '부적절한 행동'), ('spam', '스팸/광고'), ('other', '기타')], max_length=30, verbose_name='신고유형')),
                ('description', models.TextField(verbose_name='신고내용')),
                ('status', models.CharField(choices=[('pending', '대기중'), ('processing', '처리중'), ('resolved', '해결됨'), ('rejected', '거부됨')], default='pending', max_length=20, verbose_name='처리상태')),
                ('admin_note', models.TextField(blank=True, null=True, verbose_name='관리자메모')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='처리일시')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_used_phone_reports', to=settings.AUTH_USER_MODEL, verbose_name='처리자')),
                ('reported_phone', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='used_phones.usedphone', verbose_name='신고상품')),
                ('reported_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_used_phone_reports', to=settings.AUTH_USER_MODEL, verbose_name='신고대상')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submitted_used_phone_reports', to=settings.AUTH_USER_MODEL, verbose_name='신고자')),
            ],
            options={
                'verbose_name': '중고폰 신고',
                'verbose_name_plural': '중고폰 신고',
                'db_table': 'used_phone_reports',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UsedPhonePenalty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('penalty_type', models.CharField(choices=[('auto_report', '신고 누적'), ('manual_admin', '관리자 수동'), ('trade_violation', '거래 위반'), ('fake_listing', '허위매물'), ('abusive_behavior', '악성 행위')], max_length=20, verbose_name='패널티유형')),
                ('reason', models.TextField(verbose_name='패널티사유')),
                ('duration_days', models.IntegerField(verbose_name='패널티일수')),
                ('start_date', models.DateTimeField(auto_now_add=True, verbose_name='시작일')),
                ('end_date', models.DateTimeField(verbose_name='종료일')),
                ('status', models.CharField(choices=[('active', '활성'), ('expired', '만료'), ('revoked', '해제')], default='active', max_length=20, verbose_name='상태')),
                ('revoked_at', models.DateTimeField(blank=True, null=True, verbose_name='해제일시')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('issued_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_used_phone_penalties', to=settings.AUTH_USER_MODEL, verbose_name='발령자')),
                ('related_reports', models.ManyToManyField(blank=True, related_name='penalties', to='used_phones.usedphonereport', verbose_name='관련신고')),
                ('revoked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='revoked_used_phone_penalties', to=settings.AUTH_USER_MODEL, verbose_name='해제자')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phone_penalties', to=settings.AUTH_USER_MODEL, verbose_name='패널티대상')),
            ],
            options={
                'verbose_name': '중고폰 패널티',
                'verbose_name_plural': '중고폰 패널티',
                'db_table': 'used_phone_penalties',
                'ordering': ['-created_at'],
            },
        ),
    ]