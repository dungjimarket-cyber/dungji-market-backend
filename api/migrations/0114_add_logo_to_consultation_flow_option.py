# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0113_fix_merged_category_flows'),
    ]

    operations = [
        migrations.AddField(
            model_name='consultationflowoption',
            name='logo',
            field=models.CharField(blank=True, default='', help_text='예: /logos/skt.png', max_length=100, verbose_name='로고 이미지 경로'),
        ),
    ]
