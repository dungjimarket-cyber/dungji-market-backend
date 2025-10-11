# Generated manually for SMSLog model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0093_add_image_field_to_custom_groupbuy_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='SMSLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=20, verbose_name='전화번호')),
                ('message_type', models.CharField(
                    choices=[
                        ('verification', '인증번호'),
                        ('groupbuy_completion', '공구 마감 알림'),
                        ('custom', '기타')
                    ],
                    max_length=30,
                    verbose_name='메시지 유형'
                )),
                ('message_content', models.TextField(verbose_name='메시지 내용')),
                ('status', models.CharField(
                    choices=[
                        ('success', '발송 성공'),
                        ('failed', '발송 실패')
                    ],
                    max_length=20,
                    verbose_name='발송 상태'
                )),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='오류 메시지')),
                ('sent_at', models.DateTimeField(auto_now_add=True, verbose_name='발송 시간')),
                ('custom_groupbuy', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sms_logs',
                    to='api.customgroupbuy',
                    verbose_name='관련 공구'
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sms_logs',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='수신자'
                )),
            ],
            options={
                'verbose_name': 'SMS 발송 내역',
                'verbose_name_plural': 'SMS 발송 내역',
                'db_table': 'sms_log',
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['-sent_at'], name='sms_log_sent_at_idx'),
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['status'], name='sms_log_status_idx'),
        ),
        migrations.AddIndex(
            model_name='smslog',
            index=models.Index(fields=['message_type'], name='sms_log_msg_type_idx'),
        ),
    ]
