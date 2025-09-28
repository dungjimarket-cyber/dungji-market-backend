# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0086_custom_groupbuy_products'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customgroupbuy',
            name='title',
            field=models.CharField(max_length=50, verbose_name='제목'),
        ),
    ]