# Generated manually for TradeCancellation model and price validators

from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0008_update_offer_count'),
    ]

    operations = [
        # TradeCancellation 모델 생성
        migrations.CreateModel(
            name='TradeCancellation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancelled_by', models.CharField(choices=[('seller', '판매자'), ('buyer', '구매자')], max_length=10)),
                ('reason', models.CharField(choices=[
                    ('change_mind', '단순 변심'),
                    ('found_better', '더 나은 조건 발견'),
                    ('no_response', '상대방 연락 두절'),
                    ('condition_mismatch', '상품 상태 불일치'),
                    ('price_disagreement', '가격 재협상 실패'),
                    ('schedule_conflict', '일정 조율 실패'),
                    ('location_issue', '거래 장소 문제'),
                    ('other', '기타'),
                ], max_length=50)),
                ('custom_reason', models.TextField(blank=True, null=True, verbose_name='기타 사유')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('canceller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trade_cancellations', to='auth.user')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cancellations', to='used_phones.usedphoneoffer')),
                ('phone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cancellations', to='used_phones.usedphone')),
            ],
            options={
                'verbose_name': '거래 취소 기록',
                'verbose_name_plural': '거래 취소 기록',
                'db_table': 'trade_cancellations',
                'ordering': ['-created_at'],
            },
        ),
        
        # 가격 필드에 최대값 검증 추가
        migrations.AlterField(
            model_name='usedphone',
            name='price',
            field=models.IntegerField(
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(9900000)
                ],
                verbose_name='판매가격'
            ),
        ),
        migrations.AlterField(
            model_name='usedphone',
            name='min_offer_price',
            field=models.IntegerField(
                blank=True,
                null=True,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(9900000)
                ],
                verbose_name='최소제안가격'
            ),
        ),
    ]