# Generated migration for custom_photo field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),  # 최신 마이그레이션 번호로 자동 조정됨
    ]

    operations = [
        migrations.AddField(
            model_name='localbusiness',
            name='custom_photo',
            field=models.ImageField(blank=True, help_text='Google 이미지가 없을 경우 직접 업로드', null=True, upload_to='local_business_photos/', verbose_name='커스텀 이미지'),
        ),
    ]
