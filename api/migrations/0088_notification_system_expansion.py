# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0069_noshow_objection'),
    ]

    operations = [
        # 1. Notification 모델 확장
        migrations.AlterField(
            model_name='notification',
            name='groupbuy',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='api.groupbuy',
                verbose_name='공구'
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='item_type',
            field=models.CharField(
                blank=True,
                choices=[('groupbuy', '공구'), ('phone', '휴대폰'), ('electronics', '전자제품')],
                max_length=20,
                null=True,
                verbose_name='아이템 타입'
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='item_id',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='아이템 ID'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to=settings.AUTH_USER_MODEL,
                verbose_name='사용자'
            ),
        ),
        migrations.AlterField(
            model_name='notification',
            name='message',
            field=models.TextField(verbose_name='메시지'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('reminder', '리마인더'),
                    ('success', '성공/최종선정'),
                    ('failure', '실패/취소'),
                    ('info', '정보/상태변경'),
                    ('bid_selected', '견적 최종 선정'),
                    ('bid_rejected', '견적 탈락'),
                    ('buyer_decision_started', '구매 확정 대기'),
                    ('seller_decision_started', '판매 확정 대기'),
                    ('all_cancelled', '공구 취소'),
                    ('deal_confirmed_seller', '거래 확정 (판매자)'),
                    ('deal_confirmed_buyer', '거래 확정 (구매자)'),
                    ('offer_received', '가격 제안 수신'),
                    ('offer_accepted', '가격 제안 수락'),
                    ('trade_cancelled', '거래 취소'),
                    ('trade_completed', '거래 완료'),
                    ('marketing', '마케팅/이벤트'),
                ],
                default='info',
                max_length=30,
                verbose_name='알림 타입'
            ),
        ),
        migrations.AlterField(
            model_name='notification',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='생성일'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='is_read',
            field=models.BooleanField(default=False, verbose_name='읽음 여부'),
        ),
        migrations.AlterModelOptions(
            name='notification',
            options={
                'ordering': ['-created_at'],
                'verbose_name': '알림',
                'verbose_name_plural': '알림 관리',
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', '-created_at'], name='api_notific_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read'], name='api_notific_user_id_is_read_idx'),
        ),

        # 2. NotificationSetting 모델 생성
        migrations.CreateModel(
            name='NotificationSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trade_notifications', models.BooleanField(default=True, verbose_name='거래 알림')),
                ('marketing_notifications', models.BooleanField(default=False, verbose_name='마케팅 알림')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notification_settings',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='사용자'
                )),
            ],
            options={
                'verbose_name': '알림 설정',
                'verbose_name_plural': '알림 설정 관리',
            },
        ),

        # 3. PushToken 모델 생성
        migrations.CreateModel(
            name='PushToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=255, unique=True, verbose_name='푸시 토큰')),
                ('platform', models.CharField(
                    choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')],
                    max_length=10,
                    verbose_name='플랫폼'
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='활성 상태')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='push_tokens',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='사용자'
                )),
            ],
            options={
                'verbose_name': '푸시 토큰',
                'verbose_name_plural': '푸시 토큰 관리',
            },
        ),
        migrations.AddIndex(
            model_name='pushtoken',
            index=models.Index(fields=['user', 'is_active'], name='api_pushtok_user_id_is_active_idx'),
        ),
    ]
