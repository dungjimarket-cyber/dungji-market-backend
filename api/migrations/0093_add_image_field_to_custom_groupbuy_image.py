# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0092_add_custom_penalty_missing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='customgroupbuyimage',
            name='image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='custom_groupbuys/%Y/%m/%d/',
                verbose_name='이미지'
            ),
        ),
        migrations.AlterField(
            model_name='customgroupbuyimage',
            name='image_url',
            field=models.TextField(blank=True, verbose_name='이미지 URL'),
        ),
    ]
