# Generated migration for image upload enhancements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usedphoneimage',
            name='image_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='이미지 URL'),
        ),
        migrations.AddField(
            model_name='usedphoneimage',
            name='thumbnail_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='썸네일 URL'),
        ),
        migrations.AddField(
            model_name='usedphoneimage',
            name='width',
            field=models.IntegerField(blank=True, null=True, verbose_name='가로크기'),
        ),
        migrations.AddField(
            model_name='usedphoneimage',
            name='height',
            field=models.IntegerField(blank=True, null=True, verbose_name='세로크기'),
        ),
        migrations.AddField(
            model_name='usedphoneimage',
            name='file_size',
            field=models.IntegerField(blank=True, null=True, verbose_name='파일크기'),
        ),
    ]