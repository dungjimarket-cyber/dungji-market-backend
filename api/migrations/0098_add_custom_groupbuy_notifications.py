from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0097_add_seller_category'),
    ]

    operations = [
        # Notification 모델에 custom_groupbuy 필드 추가
        migrations.AddField(
            model_name='notification',
            name='custom_groupbuy',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='api.customgroupbuy',
                verbose_name='커스텀 공구'
            ),
        ),

        # Notification의 NOTIFICATION_TYPES choices 업데이트
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
                    ('custom_completed', '커스텀 공구 마감'),
                    ('custom_expired', '커스텀 공구 종료'),
                    ('custom_cancelled', '커스텀 공구 취소'),
                    ('custom_code_issued', '커스텀 할인코드 발급'),
                    ('offer_received', '가격 제안 수신'),
                    ('offer_accepted', '가격 제안 수락'),
                    ('trade_cancelled', '거래 취소'),
                    ('trade_completed', '거래 완료'),
                    ('marketing', '마케팅/이벤트'),
                ],
                max_length=30,
                verbose_name='알림 타입'
            ),
        ),

        # ITEM_TYPE_CHOICES 업데이트
        migrations.AlterField(
            model_name='notification',
            name='item_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('groupbuy', '공구'),
                    ('custom', '커스텀 공구'),
                    ('phone', '휴대폰'),
                    ('electronics', '전자제품'),
                ],
                max_length=20,
                null=True,
                verbose_name='아이템 타입'
            ),
        ),
    ]
