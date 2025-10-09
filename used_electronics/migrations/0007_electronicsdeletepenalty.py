# Generated manually for ElectronicsDeletePenalty model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_electronics', '0006_electronicstradecancellation'),
    ]

    operations = [
        # 먼저 모델 정의
        migrations.CreateModel(
            name='ElectronicsDeletePenalty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('electronics_model', models.CharField(max_length=100, verbose_name='삭제된 상품명')),
                ('had_offers', models.BooleanField(default=False, verbose_name='견적 존재 여부')),
                ('penalty_end', models.DateTimeField(verbose_name='패널티 종료 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='electronics_delete_penalties', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '전자제품 삭제 패널티',
                'verbose_name_plural': '전자제품 삭제 패널티',
                'db_table': 'electronics_delete_penalties',
                'ordering': ['-created_at'],
            },
        ),
    ]
