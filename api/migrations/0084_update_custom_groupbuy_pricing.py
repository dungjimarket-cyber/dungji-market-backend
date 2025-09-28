# Generated manually

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0083_custom_groupbuy_models'),
    ]

    operations = [
        # 1. pricing_type 필드 추가
        migrations.AddField(
            model_name='customgroupbuy',
            name='pricing_type',
            field=models.CharField(
                choices=[('single_product', '단일상품'), ('all_products', '전품목 할인')],
                default='single_product',
                max_length=20,
                verbose_name='가격 유형'
            ),
        ),
        # 2. product_name 필드 추가
        migrations.AddField(
            model_name='customgroupbuy',
            name='product_name',
            field=models.CharField(
                blank=True,
                help_text='단일상품인 경우 상품명 입력',
                max_length=200,
                null=True,
                verbose_name='상품명'
            ),
        ),
        # 3. original_price nullable로 변경
        migrations.AlterField(
            model_name='customgroupbuy',
            name='original_price',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='단일상품인 경우 정가 입력',
                null=True,
                verbose_name='정가'
            ),
        ),
        # 4. max_wait_hours nullable로 변경
        migrations.AlterField(
            model_name='customgroupbuy',
            name='max_wait_hours',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='24~720시간 (1~30일), 미설정 시 무제한',
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(24),
                    django.core.validators.MaxValueValidator(720)
                ],
                verbose_name='최대 대기 시간(시간)'
            ),
        ),
        # 5. expired_at nullable로 변경
        migrations.AlterField(
            model_name='customgroupbuy',
            name='expired_at',
            field=models.DateTimeField(
                blank=True,
                help_text='max_wait_hours 설정 시 자동 계산',
                null=True,
                verbose_name='만료 시간'
            ),
        ),
    ]