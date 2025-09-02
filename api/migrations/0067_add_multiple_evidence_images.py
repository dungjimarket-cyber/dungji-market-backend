# Generated manually for multiple evidence images in NoShowReport

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0066_notification_type_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='noshowreport',
            name='evidence_image_2',
            field=models.ImageField(blank=True, null=True, upload_to='noshow_reports/', verbose_name='증빙 이미지 2'),
        ),
        migrations.AddField(
            model_name='noshowreport',
            name='evidence_image_3',
            field=models.ImageField(blank=True, null=True, upload_to='noshow_reports/', verbose_name='증빙 이미지 3'),
        ),
    ]