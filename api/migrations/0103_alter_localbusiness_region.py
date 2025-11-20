# Generated manually - change region from ForeignKey to CharField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0102_local_business_models'),
    ]

    operations = [
        # 1. 기존 region ForeignKey 제거
        migrations.RemoveField(
            model_name='localbusiness',
            name='region',
        ),

        # 2. 새로운 region_name CharField 추가
        migrations.AddField(
            model_name='localbusiness',
            name='region_name',
            field=models.CharField(
                max_length=50,
                verbose_name='지역명',
                help_text='예: 강남구, 수원시',
                db_index=True,
                default='강남구'
            ),
            preserve_default=False,
        ),

        # 3. Meta ordering 업데이트
        migrations.AlterModelOptions(
            name='localbusiness',
            options={
                'verbose_name': '지역 업체',
                'verbose_name_plural': '지역 업체',
                'ordering': ['region_name', 'category', 'rank_in_region']
            },
        ),

        # 4. 기존 인덱스 제거
        migrations.RemoveIndex(
            model_name='localbusiness',
            name='local_busin_region__b2e1f4_idx',
        ),

        # 5. 새로운 인덱스 추가
        migrations.AddIndex(
            model_name='localbusiness',
            index=models.Index(
                fields=['region_name', 'category', 'rank_in_region'],
                name='local_busin_region__new_idx'
            ),
        ),
    ]
