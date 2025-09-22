"""
통합 찜/후기 모델 마이그레이션 (단순 버전)
"""
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0080_add_unified_report_penalty_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnifiedFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('phone', '휴대폰'), ('electronics', '전자제품')], max_length=20, verbose_name='상품 유형')),
                ('item_id', models.PositiveIntegerField(verbose_name='상품 ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='찜한 날짜')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unified_favorites', to='api.user')),
            ],
            options={
                'verbose_name': '통합 찜',
                'verbose_name_plural': '통합 찜 관리',
                'db_table': 'unified_favorites',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'item_type', 'item_id')},
            },
        ),
        migrations.CreateModel(
            name='UnifiedReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('phone', '휴대폰'), ('electronics', '전자제품')], max_length=20, verbose_name='상품 유형')),
                ('item_id', models.PositiveIntegerField(verbose_name='상품 ID')),
                ('transaction_type', models.CharField(choices=[('buy', '구매'), ('sell', '판매')], max_length=10, verbose_name='거래 유형')),
                ('rating', models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='평점')),
                ('comment', models.TextField(blank=True, max_length=500, verbose_name='후기 내용')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='후기 작성일')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='written_reviews', to='api.user')),
                ('reviewed_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_reviews', to='api.user')),
            ],
            options={
                'verbose_name': '통합 후기',
                'verbose_name_plural': '통합 후기 관리',
                'db_table': 'unified_reviews',
                'ordering': ['-created_at'],
                'unique_together': {('reviewer', 'reviewed_user', 'item_type', 'item_id')},
            },
        ),
    ]