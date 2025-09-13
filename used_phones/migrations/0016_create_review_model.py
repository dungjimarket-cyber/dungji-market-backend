# Generated manually for UsedPhoneTransaction and UsedPhoneReview models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_phones', '0015_fix_related_name_conflicts'),
    ]

    operations = [
        # Create UsedPhoneTransaction first (required by UsedPhoneReview)
        migrations.CreateModel(
            name='UsedPhoneTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=0, max_digits=10, verbose_name='거래 금액')),
                ('status', models.CharField(choices=[('pending', '대기중'), ('completed', '완료'), ('cancelled', '취소')], default='pending', max_length=20, verbose_name='거래 상태')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='완료일')),
                ('cancelled_at', models.DateTimeField(blank=True, null=True, verbose_name='취소일')),
                ('seller_confirmed', models.BooleanField(default=False, verbose_name='판매자 확인')),
                ('buyer_confirmed', models.BooleanField(default=False, verbose_name='구매자 확인')),
                ('seller_confirmed_at', models.DateTimeField(blank=True, null=True, verbose_name='판매자 확인 시간')),
                ('buyer_confirmed_at', models.DateTimeField(blank=True, null=True, verbose_name='구매자 확인 시간')),
                ('phone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='used_phones.usedphone', verbose_name='중고폰')),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phone_purchases', to=settings.AUTH_USER_MODEL, verbose_name='구매자')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phone_sales', to=settings.AUTH_USER_MODEL, verbose_name='판매자')),
                ('offer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transaction', to='used_phones.usedphoneoffer', verbose_name='제안')),
            ],
            options={
                'verbose_name': '중고폰 거래',
                'verbose_name_plural': '중고폰 거래',
                'db_table': 'used_phone_transactions',
                'ordering': ['-created_at'],
            },
        ),
        # Then create UsedPhoneReview model
        migrations.CreateModel(
            name='UsedPhoneReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], verbose_name='평점')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='후기 내용')),
                ('is_punctual', models.BooleanField(default=False, verbose_name='시간약속 잘 지킴')),
                ('is_friendly', models.BooleanField(default=False, verbose_name='친절함')),
                ('is_honest', models.BooleanField(default=False, verbose_name='정직함')),
                ('is_fast_response', models.BooleanField(default=False, verbose_name='빠른 응답')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='작성일')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='used_phones.usedphonetransaction', verbose_name='거래')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='given_used_phone_reviews', to=settings.AUTH_USER_MODEL, verbose_name='평가자')),
                ('reviewee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_used_phone_reviews', to=settings.AUTH_USER_MODEL, verbose_name='평가 대상')),
            ],
            options={
                'verbose_name': '중고폰 거래 후기',
                'verbose_name_plural': '중고폰 거래 후기',
                'db_table': 'used_phone_reviews',
                'ordering': ['-created_at'],
                'unique_together': {('transaction', 'reviewer')},
            },
        ),
    ]