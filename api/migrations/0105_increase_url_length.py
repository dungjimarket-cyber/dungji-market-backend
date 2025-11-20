from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0104_alter_localbusiness_latitude_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='localbusiness',
            name='google_maps_url',
            field=models.URLField(blank=True, max_length=1000, verbose_name='구글 지도 URL'),
        ),
        migrations.AlterField(
            model_name='localbusiness',
            name='photo_url',
            field=models.URLField(blank=True, max_length=1000, null=True, verbose_name='대표 사진 URL'),
        ),
    ]
