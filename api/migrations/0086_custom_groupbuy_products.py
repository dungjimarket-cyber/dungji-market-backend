# Generated manually

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0085_custom_noshow_penalty'),
    ]

    operations = [
        # products JSONField 추가
        migrations.AddField(
            model_name='customgroupbuy',
            name='products',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='단일상품 최대 10개 [{"name": "상품명", "original_price": 100000, "discount_rate": 10}]',
                verbose_name='상품 목록'
            ),
        ),
        # 기존 필드 nullable 및 help_text 변경
        migrations.AlterField(
            model_name='customgroupbuy',
            name='product_name',
            field=models.CharField(
                blank=True,
                help_text='(구버전 - products 필드 사용 권장)',
                max_length=200,
                null=True,
                verbose_name='상품명 (구버전)'
            ),
        ),
        migrations.AlterField(
            model_name='customgroupbuy',
            name='original_price',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='(구버전 - products 필드 사용 권장)',
                null=True,
                verbose_name='정가 (구버전)'
            ),
        ),
        migrations.AlterField(
            model_name='customgroupbuy',
            name='discount_rate',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='전품목 할인 시 사용',
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100)
                ],
                verbose_name='할인율 (전품목용)'
            ),
        ),
    ]