# Generated manually for ElectronicsTradeCancellation model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_electronics', '0005_add_timestamp_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ElectronicsTradeCancellation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancelled_by', models.CharField(choices=[('seller', '판매자'), ('buyer', '구매자')], max_length=10)),
                ('reason', models.CharField(choices=[('change_mind', '단순 변심'), ('found_better', '다른 상품 구매 결정'), ('seller_no_response', '판매자 연락 두절'), ('condition_mismatch', '상품 상태가 설명과 다름'), ('price_disagreement', '추가 비용 요구'), ('seller_cancel_request', '판매자 취소 요청'), ('product_sold', '다른 경로로 판매됨'), ('buyer_no_response', '구매자 연락 두절'), ('buyer_no_show', '구매자 약속 불이행'), ('payment_issue', '결제 문제 발생'), ('buyer_unreasonable', '구매자 무리한 요구'), ('buyer_cancel_request', '구매자 취소 요청'), ('personal_reason', '개인 사정으로 판매 불가'), ('schedule_conflict', '거래 일정 조율 실패'), ('location_issue', '거래 장소 문제'), ('other', '기타')], max_length=50)),
                ('custom_reason', models.TextField(blank=True, null=True, verbose_name='기타 사유')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('canceller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='electronics_trade_cancellations', to=settings.AUTH_USER_MODEL)),
                ('electronics', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cancellations', to='used_electronics.usedelectronics')),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cancellations', to='used_electronics.electronicsoffer')),
            ],
            options={
                'verbose_name': '전자제품 거래 취소 기록',
                'verbose_name_plural': '전자제품 거래 취소 기록',
                'db_table': 'electronics_trade_cancellations',
                'ordering': ['-created_at'],
            },
        ),
    ]