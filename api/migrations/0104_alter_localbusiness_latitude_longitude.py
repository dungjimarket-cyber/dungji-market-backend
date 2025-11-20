# Generated manually - allow null for latitude and longitude

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0103_alter_localbusiness_region'),
    ]

    operations = [
        migrations.AlterField(
            model_name='localbusiness',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name='위도'
            ),
        ),
        migrations.AlterField(
            model_name='localbusiness',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name='경도'
            ),
        ),
    ]
