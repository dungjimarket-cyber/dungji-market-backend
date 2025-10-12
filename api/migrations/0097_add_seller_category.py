from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0096_add_show_in_custom_to_notice'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='seller_category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('telecom', '통신상품판매(휴대폰,인터넷,TV개통 등)'),
                    ('rental', '렌탈서비스판매(정수기,비데,매트리스 등)'),
                    ('electronics', '가전제품판매(냉장고,세탁기,컴퓨터 등)'),
                    ('general', '온/오프라인 도소매,요식업 등'),
                ],
                max_length=30,
                null=True,
                verbose_name='판매회원 구분'
            ),
        ),
    ]
