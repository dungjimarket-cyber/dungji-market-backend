# Generated manually for nullable target_participants

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0099_add_deal_type_to_custom_groupbuy'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customgroupbuy',
            name='target_participants',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='기간특가는 null 가능',
                null=True,
                validators=[MinValueValidator(2), MaxValueValidator(2000)],
                verbose_name='목표 인원'
            ),
        ),
    ]
