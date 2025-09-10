"""
공구와 동일한 지역 필드 추가
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0005_auto_create_sample_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='usedphone',
            name='region_type',
            field=models.CharField(default='local', max_length=20, verbose_name='지역 유형'),
        ),
        migrations.AddField(
            model_name='usedphone',
            name='region_name',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='지역명 백업'),
        ),
    ]