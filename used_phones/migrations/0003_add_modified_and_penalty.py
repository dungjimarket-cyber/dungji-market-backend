# Generated manually for adding is_modified field and UsedPhoneDeletePenalty model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_phones', '0002_usedphone_meeting_place_usedphoneregion'),
    ]

    operations = [
        # Add is_modified field to UsedPhone
        migrations.AddField(
            model_name='usedphone',
            name='is_modified',
            field=models.BooleanField(default=False, verbose_name='수정됨 표시'),
        ),
        
        # Update UsedPhoneOffer amount field with max validator
        migrations.AlterField(
            model_name='usedphoneoffer',
            name='amount',
            field=models.IntegerField(
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(9900000)
                ],
                verbose_name='제안금액'
            ),
        ),
        
        # Create UsedPhoneDeletePenalty model
        migrations.CreateModel(
            name='UsedPhoneDeletePenalty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_model', models.CharField(max_length=100, verbose_name='삭제된 상품명')),
                ('had_offers', models.BooleanField(default=False, verbose_name='견적 존재 여부')),
                ('penalty_end', models.DateTimeField(verbose_name='패널티 종료 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phone_penalties', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '삭제 패널티',
                'verbose_name_plural': '삭제 패널티',
                'db_table': 'used_phone_delete_penalties',
                'ordering': ['-created_at'],
            },
        ),
    ]