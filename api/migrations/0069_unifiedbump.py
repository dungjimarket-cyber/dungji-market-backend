# Generated manually for UnifiedBump model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0068_auto_20250123_0000'),  # Adjust to your last migration
    ]

    operations = [
        migrations.CreateModel(
            name='UnifiedBump',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('phone', '휴대폰'), ('electronics', '전자제품')], max_length=20, verbose_name='상품타입')),
                ('item_id', models.PositiveIntegerField(db_index=True, verbose_name='상품ID')),
                ('bumped_at', models.DateTimeField(auto_now_add=True, verbose_name='끌올시간')),
                ('is_free', models.BooleanField(default=True, verbose_name='무료여부')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bump_history', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '통합 끌올',
                'verbose_name_plural': '통합 끌올 관리',
                'db_table': 'unified_bumps',
                'ordering': ['-bumped_at'],
                'indexes': [
                    models.Index(fields=['user', '-bumped_at'], name='unified_bum_user_id_3b6f17_idx'),
                    models.Index(fields=['item_type', 'item_id', '-bumped_at'], name='unified_bum_item_ty_a7e2c9_idx'),
                    models.Index(fields=['user', 'bumped_at'], name='unified_bum_user_id_9c3d82_idx'),
                ],
            },
        ),
    ]